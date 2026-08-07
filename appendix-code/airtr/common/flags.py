"""
AIRTR flag registry.

Every flag is a BENIGN marker of the form AIRTR{...}. Capturing one proves an
exploit worked without causing real harm. Flags are intentionally deterministic
so the scoreboard can validate captures. NONE of these are secrets and none map
to any real system.
"""

FLAGS = {
    # Module 1 — Introduction / surface / instruction-data collapse
    "m1_surface":        "AIRTR{m1_attack_surface_mapped}",
    "m1_indirect":       "AIRTR{m1_first_indirect_injection}",
    "m1_frames":         "AIRTR{m1_instruction_data_collapse}",

    # Module 2 — Reconnaissance
    "m2_fingerprint":    "AIRTR{m2_selfhosted_openai_compatible_backend}",
    "m2_osint":          "AIRTR{m2_architecture_from_osint}",
    "m2_discovery":      "AIRTR{m2_unauthenticated_vector_store}",
    "m2_channels":       "AIRTR{m2_injection_channels_mapped}",

    # Module 3 — Attacking agents
    "m3_prompt":         "AIRTR{m3_system_prompt_extracted}",
    "m3_indirect":       "AIRTR{m3_indirect_injection_tool_hijack}",
    "m3_memory":         "AIRTR{m3_memory_poisoning_persistence}",
    "m3_sqli":           "AIRTR{m3_insecure_output_handling_sqli}",
    "m3_evasion":        "AIRTR{m3_guardrail_evasion}",
    "m3_compose":        "AIRTR{m3_composed_multiclass_payload}",
    "m3_chain":          "AIRTR{m3_full_hijack_chain}",

    # Module 4 — Multi-agent / A2A
    "m4_topology":       "AIRTR{m4_trust_edges_identified}",
    "m4_propagation":    "AIRTR{m4_trust_laundering_cascade}",
    "m4_impersonation":  "AIRTR{m4_orchestrator_impersonation}",
    "m4_reviewer":       "AIRTR{m4_reviewer_subverted}",
    "m4_card":           "AIRTR{m4_discovery_card_poisoning}",
    "m4_cascade":        "AIRTR{m4_full_cascade}",
    "m4_bypass":         "AIRTR{m4_downstream_role_impersonation}",

    # Module 5 — RAG
    "m5_channels":       "AIRTR{m5_ingestion_channels_enumerated}",
    "m5_content":        "AIRTR{m5_content_poisoning_relevance}",
    "m5_exfil":          "AIRTR{m5_rag_instruction_poisoning_exfil}",
    "m5_xtenant":        "AIRTR{m5_cross_tenant_retrieval_bypass}",
    "m5_index":          "AIRTR{m5_direct_index_manipulation}",
    "m5_reranker":       "AIRTR{m5_beat_the_reranker}",
    "m5_persist":        "AIRTR{m5_persistent_query_targeted_exfil}",
    "m5_corruption":     "AIRTR{m5_denial_of_correct_answer}",

    # Module 6 — Embeddings
    "m6_dump":           "AIRTR{m6_exposed_vector_store_dump}",
    "m6_inversion":      "AIRTR{m6_embedding_inversion_recovered}",
    "m6_nn":             "AIRTR{m6_nearest_neighbor_recovery}",
    "m6_infer":          "AIRTR{m6_membership_attribute_inference}",
    "m6_magnet":         "AIRTR{m6_retrieval_magnet}",
    "m6_oracle":         "AIRTR{m6_similarity_oracle_leak}",
    "m6_linkage":        "AIRTR{m6_record_linkage_reidentification}",
    "m6_extract":        "AIRTR{m6_query_only_model_extraction}",

    # Module 7 — MCP / tools
    "m7_matrix":         "AIRTR{m7_tool_matrix_dangerous_tools}",
    "m7_deputy":         "AIRTR{m7_confused_deputy_admin_tool}",
    "m7_poisoning":      "AIRTR{m7_tool_description_injection}",
    "m7_ssrf":           "AIRTR{m7_ssrf_to_metadata_credentials}",
    "m7_exposed":        "AIRTR{m7_exposed_mcp_filesystem_server}",
    "m7_linejump":       "AIRTR{m7_line_jumping_no_invocation}",
    "m7_xserver":        "AIRTR{m7_cross_server_exfiltration}",
    "m7_traversal":      "AIRTR{m7_filesystem_traversal_secret_theft}",

    # Module 8 — Supply chain
    "m8_chain":          "AIRTR{m8_supply_chain_weak_links}",
    "m8_pickle":         "AIRTR{m8_malicious_pickle_on_load}",
    "m8_backdoor":       "AIRTR{m8_backdoored_adapter_trigger}",
    "m8_swap":           "AIRTR{m8_registry_model_swap}",
    "m8_deps":           "AIRTR{m8_dependency_provenance_audit}",
    "m8_hunt":           "AIRTR{m8_behavioral_backdoor_hunt}",
    "m8_adapter_chain":  "AIRTR{m8_adapter_to_production_backdoor}",

    # Module 9 — Infrastructure
    "m9_mgmt":           "AIRTR{m9_unauth_management_rce}",
    "m9_secrets":        "AIRTR{m9_notebook_secret_harvest}",
    "m9_pivot":          "AIRTR{m9_ssrf_metadata_overprivileged_iam}",
    "m9_rbac":           "AIRTR{m9_rbac_escalation}",
    "m9_dos":            "AIRTR{m9_model_denial_of_wallet}",
    "m9_imds":           "AIRTR{m9_imdsv2_breaks_ssrf}",

    # Module 10 — Threat modeling
    "m10_assets":        "AIRTR{m10_high_value_assets_ranked}",
    "m10_boundaries":    "AIRTR{m10_trust_boundaries_mapped}",
    "m10_tree":          "AIRTR{m10_attack_tree_priority_path}",

    # Module 11 — Capstone
    "capstone":          "AIRTR{capstone_full_spectrum_engagement_complete}",
}


def get(name):
    return FLAGS[name]
