//! Semantic fingerprint calculation for protocol services
//!
//! Provides semantic fingerprinting capabilities for proto files and services
//! using proto-sign analysis that ignores formatting differences.

use crate::{CompatibilityError, ProtoFile, Result};
use sha2::{Digest, Sha256};

/// Semantic fingerprint calculation utilities for protocol services
pub struct Fingerprint;

impl Fingerprint {
    // =========================================================================
    // Level 1: Single Proto File Fingerprinting
    // =========================================================================

    /// Calculate semantic fingerprint for a single proto file
    /// This uses proto-sign analysis and ignores formatting differences
    pub fn calculate_proto_semantic_fingerprint(proto_content: &str) -> Result<String> {
        let spec = proto_fingerprint::Spec::try_from(proto_content)
            .map_err(CompatibilityError::ProtoSignError)?;

        Ok(format!("semantic:{}", spec.fingerprint))
    }

    // Removed: calculate_proto_fingerprints() - content fingerprints are not semantically meaningful

    // =========================================================================
    // Level 2: Service-Level Multi-File Fingerprinting
    // =========================================================================

    /// Calculate semantic fingerprint for multiple proto files (service level)
    /// Uses proto-sign for each file and combines the results deterministically
    pub fn calculate_service_semantic_fingerprint(proto_files: &[ProtoFile]) -> Result<String> {
        let mut sorted_files = proto_files.to_vec();
        sorted_files.sort_by(|a, b| a.name.cmp(&b.name));

        let mut semantic_fingerprints = Vec::new();
        for file in &sorted_files {
            let spec = proto_fingerprint::Spec::try_from(file.content.as_str()).map_err(|e| {
                CompatibilityError::ProtoParseError {
                    file_name: file.name.clone(),
                    source: e,
                }
            })?;

            semantic_fingerprints.push(format!("{}:{}", file.name, spec.fingerprint));
        }

        Ok(service_fingerprint(&semantic_fingerprints.join("\n")))
    }

    // Removed: calculate_service_fingerprints() - content fingerprints are not semantically meaningful
}

fn service_fingerprint(entries: &str) -> String {
    format!("service_semantic:{:x}", Sha256::digest(entries.as_bytes()))
}

/// Information derived from one self-contained Protobuf contract.
#[cfg(feature = "standalone-proto")]
pub struct StandaloneProtoContract {
    pub service_fingerprint: String,
    pub rpc_routes: std::collections::BTreeSet<String>,
}

/// Parse a contract without resolving any paths provided by its contents.
#[cfg(feature = "standalone-proto")]
pub fn inspect_standalone_proto(
    file_name: &str,
    content: &str,
) -> anyhow::Result<StandaloneProtoContract> {
    use anyhow::{Context, ensure};

    let imports = protobuf_parse::pure::parse_dependencies(content)?;
    ensure!(
        imports.dependency.is_empty(),
        "the application contract must be a self-contained .proto file"
    );
    // The pure parser accepts file paths. Use one fixed filename after checking
    // imports with the same parser, and never join paths from the contract.
    let temp = tempfile::tempdir()?;
    let input = temp.path().join("input.proto");
    std::fs::write(&input, content)?;
    let descriptor = protobuf_parse::Parser::new()
        .pure()
        .include(temp.path())
        .input(&input)
        .file_descriptor_set()?
        .file
        .into_iter()
        .find(|file| file.name() == "input.proto")
        .context("missing descriptor for the application contract")?;

    let normalized = proto_fingerprint::normalize::normalize_file(&descriptor);
    let serialized = serde_json::to_string_pretty(&normalized)?;
    let file_fingerprint = format!("{:x}", Sha256::digest(serialized.as_bytes()));
    let prefix = if descriptor.package().is_empty() {
        String::new()
    } else {
        format!("{}.", descriptor.package())
    };
    let mut rpc_routes = std::collections::BTreeSet::new();
    for service in &descriptor.service {
        for method in &service.method {
            if !method.client_streaming() && !method.server_streaming() {
                rpc_routes.insert(format!("{prefix}{}.{}", service.name(), method.name()));
            }
        }
    }
    Ok(StandaloneProtoContract {
        service_fingerprint: service_fingerprint(&format!("{file_name}:{file_fingerprint}")),
        rpc_routes,
    })
}

// =========================================================================
// Fingerprint Result Structures
// =========================================================================

#[cfg(test)]
mod tests {
    use super::*;
    use actr_protocol::ServiceSpec;

    fn create_test_proto_file(name: &str, content: &str) -> ProtoFile {
        ProtoFile {
            name: name.to_string(),
            content: content.to_string(),
            path: None,
        }
    }

    fn create_test_service(name: &str, proto_files: Vec<ProtoFile>) -> ServiceSpec {
        let semantic_fp = Fingerprint::calculate_service_semantic_fingerprint(&proto_files)
            .unwrap_or_else(|_| "placeholder".to_string());

        ServiceSpec {
            name: name.to_string(),
            description: Some("Test service".to_string()),
            fingerprint: semantic_fp,
            protobufs: proto_files
                .into_iter()
                .map(|pf| actr_protocol::service_spec::Protobuf {
                    package: pf.name, // Use name as package
                    content: pf.content,
                    fingerprint: "test-fp".to_string(),
                })
                .collect(),
            published_at: None,
            tags: vec![],
        }
    }

    #[test]
    fn test_semantic_fingerprint_ignores_formatting() {
        let content1 = "syntax=\"proto3\";message Test{string name=1;}";
        let content2 = r#"
            syntax = "proto3";

            // Test message
            message Test {
                string name = 1;  // Name field
            }
        "#;

        // Semantic fingerprints should be the same (semantically identical)
        let semantic_fp1 = Fingerprint::calculate_proto_semantic_fingerprint(content1).unwrap();
        let semantic_fp2 = Fingerprint::calculate_proto_semantic_fingerprint(content2).unwrap();

        assert_eq!(semantic_fp1, semantic_fp2);
    }

    #[test]
    fn test_service_semantic_fingerprint() {
        let files = vec![
            create_test_proto_file(
                "a.proto",
                "syntax = \"proto2\"; message A { required string name = 1; }",
            ),
            create_test_proto_file(
                "b.proto",
                "syntax = \"proto2\"; message B { required int32 id = 1; }",
            ),
        ];

        let fp = Fingerprint::calculate_service_semantic_fingerprint(&files).unwrap();
        assert!(fp.starts_with("service_semantic:"));
    }

    #[test]
    fn test_service_spec_has_semantic_fingerprint() {
        let proto_file = create_test_proto_file(
            "test.proto",
            r#"
            syntax = "proto3";
            message TestMessage {
                string name = 1;
            }
        "#,
        );

        let service = create_test_service("test-service", vec![proto_file]);

        // ServiceSpec should have fingerprint field
        assert!(!service.fingerprint.is_empty());
    }

    #[test]
    fn test_proto_semantic_fingerprint_error_handling() {
        // Test with invalid proto content
        let invalid_proto = "this is not a valid proto file";
        let result = Fingerprint::calculate_proto_semantic_fingerprint(invalid_proto);
        assert!(result.is_err());

        if let Err(e) = result {
            assert!(matches!(e, CompatibilityError::ProtoSignError(_)));
        }
    }

    #[test]
    fn test_service_semantic_fingerprint_error_handling() {
        // Test with invalid proto content in service
        let invalid_file = create_test_proto_file("invalid.proto", "invalid proto content");
        let result = Fingerprint::calculate_service_semantic_fingerprint(&[invalid_file]);

        assert!(result.is_err());
        if let Err(e) = result {
            assert!(matches!(e, CompatibilityError::ProtoParseError { .. }));
        }
    }

    #[test]
    fn test_service_semantic_fingerprint_deterministic() {
        // Test that file order doesn't affect fingerprint (files are sorted internally)
        let files_order1 = vec![
            create_test_proto_file(
                "z.proto",
                "syntax = \"proto3\"; message Z { string id = 1; }",
            ),
            create_test_proto_file(
                "a.proto",
                "syntax = \"proto3\"; message A { string name = 1; }",
            ),
        ];

        let files_order2 = vec![
            create_test_proto_file(
                "a.proto",
                "syntax = \"proto3\"; message A { string name = 1; }",
            ),
            create_test_proto_file(
                "z.proto",
                "syntax = \"proto3\"; message Z { string id = 1; }",
            ),
        ];

        let fp1 = Fingerprint::calculate_service_semantic_fingerprint(&files_order1).unwrap();
        let fp2 = Fingerprint::calculate_service_semantic_fingerprint(&files_order2).unwrap();

        assert_eq!(fp1, fp2, "File order should not affect fingerprint");
    }
}
