# AI build pipeline (Module 8) — trace provenance of each artifact
base_model:   northwind/base-support-llm        # pulled BY NAME, no hash pin  [weak]
adapter:      community/better-support-tone-lora # community LoRA, unscanned   [weak]
dataset:      partner/support-corpus             # external, unverified        [weak]
registry:     http://registry-mirror:8089        # writable, no auth           [weak]
requirements:
  - langchain==0.1.16
  - qdrant-client                                # UNPINNED                    [weak]
  - reqiests==2.31.0                             # TYPOSQUAT of 'requests'     [weak]
  - transformers                                 # UNPINNED
