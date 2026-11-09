//! The signed Actrium Product v1 application descriptor.

use serde::{Deserialize, Serialize};

use crate::{ActorPackageManifest, PackError};

const COMPONENT_PROFILE: &str = "actr.component/1";

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "kebab-case", deny_unknown_fields)]
pub struct ActriumApplication {
    pub schema_version: u32,
    pub min_actrium_version: String,
    pub front_host_api: String,
    pub service_host_api: String,
    pub front: ApplicationFront,
    pub service: ApplicationService,
    pub permissions: ApplicationPermissions,
    pub components: ApplicationComponents,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "kebab-case", deny_unknown_fields)]
pub struct ApplicationFront {
    pub guest_runtime: String,
    pub guest_entry: String,
    pub keel_api: String,
    pub capability_manifest: String,
    pub contract_digest: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "kebab-case", deny_unknown_fields)]
pub struct ApplicationService {
    pub contract: String,
    pub protocol_fingerprint: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ApplicationPermissions {
    pub front: CapabilityRequests,
    pub service: CapabilityRequests,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CapabilityRequests {
    pub capabilities: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ApplicationComponents {
    pub allow: Vec<String>,
}

impl ActriumApplication {
    pub(crate) fn validate(&self, manifest: &ActorPackageManifest) -> Result<(), PackError> {
        require(
            self.schema_version == 1,
            "unsupported Actrium application schema-version",
        )?;
        require(
            manifest.workload.profile == COMPONENT_PROFILE && manifest.workload.keel.is_none(),
            "an Actrium application requires a single actr.component/1 main workload",
        )?;
        require(
            manifest
                .files
                .iter()
                .filter(|file| file.role == "workload")
                .count()
                == 1,
            "an Actrium application must declare exactly one workload file",
        )?;
        require(
            manifest.dependencies.is_empty()
                && manifest.files.iter().all(|file| file.role != "lock"),
            "this application profile supports standalone Services without Actor dependencies",
        )?;
        require(
            self.front.guest_runtime == "keel-js",
            "unsupported Actrium Guest runtime",
        )?;
        for (path, role) in [
            (&self.front.guest_entry, "resource"),
            (&self.front.capability_manifest, "profile"),
            (&self.service.contract, "contract"),
        ] {
            require(
                manifest
                    .files
                    .iter()
                    .any(|file| file.path == *path && file.role == role),
                format!("application file `{path}` must be listed with role `{role}`"),
            )?;
        }
        require(
            self.service.contract.ends_with(".proto"),
            "the application Service contract must be a .proto file",
        )?;
        for (field, digest) in [
            ("front.contract-digest", &self.front.contract_digest),
            (
                "service.protocol-fingerprint",
                &self.service.protocol_fingerprint,
            ),
        ] {
            require(
                digest.strip_prefix("sha256:").is_some_and(|hex| {
                    hex.len() == 64
                        && hex
                            .bytes()
                            .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
                }),
                format!("application {field} must be a sha256: digest"),
            )?;
        }
        Ok(())
    }
}

fn require(condition: bool, message: impl Into<String>) -> Result<(), PackError> {
    if condition {
        Ok(())
    } else {
        Err(PackError::InvalidPackage(message.into()))
    }
}

#[cfg(feature = "actrium-application")]
mod payload {
    use std::borrow::Cow;
    use std::collections::BTreeSet;

    use actr_service_compat::fingerprint::inspect_standalone_proto;
    use semver::{Version, VersionReq};
    use serde::Deserialize;
    use wasmparser::{ComponentExternalKind, Encoding, Parser, Payload};

    use super::{ActriumApplication, require};
    use crate::{
        ActorPackageManifest, DEFAULT_MAX_VERIFIED_ENTRY_BYTES, PackError, read_actor_package_file,
        util::sha256_hex, verify_actor_package,
    };

    #[derive(Deserialize)]
    #[serde(rename_all = "camelCase", deny_unknown_fields)]
    struct CapabilityManifest {
        schema_version: u32,
        keel_api: String,
        guest_entry: String,
        imports: Vec<String>,
        host_modules: HostModules,
        components: Vec<String>,
    }

    #[derive(Deserialize)]
    #[serde(deny_unknown_fields)]
    struct HostModules {
        service: ServiceModule,
    }

    #[derive(Deserialize)]
    #[serde(deny_unknown_fields)]
    struct ServiceModule {
        rpc: Vec<String>,
        events: Vec<String>,
    }

    pub(crate) struct ApplicationDigests {
        pub contract_digest: String,
        pub protocol_fingerprint: String,
        pub rpc_routes: Vec<String>,
    }

    pub(crate) fn inspect_payloads<'a>(
        manifest: &ActorPackageManifest,
        application: &ActriumApplication,
        read: impl Fn(&str) -> Result<Cow<'a, [u8]>, PackError>,
    ) -> Result<ApplicationDigests, PackError> {
        let front = &application.front;
        let service = &application.service;
        Version::parse(&application.min_actrium_version)
            .map_err(|error| invalid("min-actrium-version", error))?;
        for (field, range) in [
            ("host.api", &manifest.host.api),
            ("front-host-api", &application.front_host_api),
            ("service-host-api", &application.service_host_api),
        ] {
            VersionReq::parse(range).map_err(|error| invalid(field, error))?;
        }
        let keel_range =
            VersionReq::parse(&front.keel_api).map_err(|error| invalid("front.keel-api", error))?;

        let wasm = read(&manifest.workload.entry)?;
        validate_workload(&wasm)?;
        let guest = read(&front.guest_entry)?;
        require(
            std::str::from_utf8(&guest).is_ok_and(|js| !js.trim().is_empty()),
            "the application Guest must be a nonempty UTF-8 bundle",
        )?;
        let capability_bytes = read(&front.capability_manifest)?;
        let capabilities: CapabilityManifest = serde_json::from_slice(&capability_bytes)
            .map_err(|error| invalid("capability manifest", error))?;
        let keel_version = Version::parse(&capabilities.keel_api)
            .or_else(|_| Version::parse(&format!("{}.0", capabilities.keel_api)))
            .map_err(|error| invalid("capability manifest keelApi", error))?;
        require(
            capabilities.schema_version == 1
                && capabilities.guest_entry == front.guest_entry
                && keel_range.matches(&keel_version),
            "capability manifest schema, Guest entry or Keel API does not match the application",
        )?;
        require(
            capabilities
                .imports
                .iter()
                .any(|name| name == "host:service")
                && capabilities
                    .imports
                    .iter()
                    .all(|name| !name.starts_with("host:") || name == "host:service")
                && application
                    .permissions
                    .front
                    .capabilities
                    .iter()
                    .any(|name| name == "service"),
            "the application must declare the supported host:service import and permission",
        )?;
        require(
            capabilities
                .components
                .iter()
                .all(|name| !name.is_empty() && application.components.allow.contains(name)),
            "the capability manifest declares a component outside the application allowlist",
        )?;

        let proto = read(&service.contract)?;
        let content =
            std::str::from_utf8(&proto).map_err(|error| invalid("Service Proto", error))?;
        let file_name = service
            .contract
            .rsplit('/')
            .next()
            .unwrap_or(&service.contract);
        let contract = inspect_standalone_proto(file_name, content)
            .map_err(|error| invalid("Service Proto", error))?;
        let declared = capabilities.host_modules.service;
        require(
            declared.events.is_empty(),
            "application Service events are not supported by this profile",
        )?;
        require(
            !declared.rpc.is_empty(),
            "the capability manifest must declare a Service RPC",
        )?;
        let mut routes = BTreeSet::new();
        for route in &declared.rpc {
            require(
                routes.insert(route) && contract.rpc_routes.contains(route),
                format!(
                    "capability manifest RPC `{route}` is duplicated or absent from the local Service contract"
                ),
            )?;
        }

        let fingerprint = contract
            .service_fingerprint
            .strip_prefix("service_semantic:")
            .ok_or_else(|| {
                PackError::InvalidPackage("unexpected Service fingerprint format".into())
            })?;
        Ok(ApplicationDigests {
            contract_digest: format!("sha256:{}", sha256_hex(&capability_bytes)),
            protocol_fingerprint: format!("sha256:{fingerprint}"),
            rpc_routes: declared.rpc,
        })
    }

    fn validate_workload(bytes: &[u8]) -> Result<(), PackError> {
        let mut depth = 0usize;
        let mut exported_workload = false;
        for payload in Parser::new(0).parse_all(bytes) {
            match payload.map_err(|error| invalid("Service WASM", error))? {
                Payload::Version { encoding, .. } if depth == 0 => {
                    require(
                        encoding == Encoding::Component,
                        "the Service must be a WASM Component",
                    )?;
                }
                Payload::ModuleSection { .. } | Payload::ComponentSection { .. } => depth += 1,
                Payload::End(_) if depth > 0 => depth -= 1,
                Payload::ComponentExportSection(exports) if depth == 0 => {
                    for export in exports {
                        let export =
                            export.map_err(|error| invalid("Service WASM export", error))?;
                        exported_workload |= export.kind == ComponentExternalKind::Instance
                            && export.name.name == "actr:workload/workload@0.8.0";
                    }
                }
                _ => {}
            }
        }
        require(
            exported_workload,
            "the Service component must export actr:workload/workload@0.8.0",
        )
    }

    fn invalid(field: &str, error: impl std::fmt::Display) -> PackError {
        PackError::InvalidPackage(format!("invalid {field}: {error}"))
    }

    /// Application inputs taken from the same archive that passed verification.
    pub struct VerifiedActriumApplication {
        pub manifest: ActorPackageManifest,
        pub wasm: Vec<u8>,
        pub guest: Vec<u8>,
        pub rpc_routes: Vec<String>,
    }

    /// Verify the container and then the signed Front–Service contract.
    pub fn verify_actrium_application(
        bytes: &[u8],
        public_key: &ed25519_dalek::VerifyingKey,
    ) -> Result<VerifiedActriumApplication, PackError> {
        let verified = verify_actor_package(bytes, public_key)?;
        let application = verified.manifest.actrium_application().ok_or_else(|| {
            PackError::InvalidPackage("missing Actrium application extension".into())
        })?;
        let read = |path: &str| {
            read_actor_package_file(bytes, &verified, path, DEFAULT_MAX_VERIFIED_ENTRY_BYTES)
        };
        let digests = inspect_payloads(&verified.manifest, application, |path| {
            read(path).map(Cow::Owned)
        })?;
        require(
            application.front.contract_digest == digests.contract_digest,
            "signed application capability digest does not match the manifest bytes",
        )?;
        require(
            application.service.protocol_fingerprint == digests.protocol_fingerprint,
            "signed application protocol fingerprint does not match the Service Proto",
        )?;
        let wasm = read(&verified.manifest.workload.entry)?;
        let guest = read(&application.front.guest_entry)?;
        Ok(VerifiedActriumApplication {
            manifest: verified.manifest,
            wasm,
            guest,
            rpc_routes: digests.rpc_routes,
        })
    }
}

#[cfg(feature = "actrium-application")]
pub(crate) use payload::inspect_payloads;
#[cfg(feature = "actrium-application")]
pub use payload::{VerifiedActriumApplication, verify_actrium_application};
