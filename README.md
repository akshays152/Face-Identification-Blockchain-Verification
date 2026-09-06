# RecallX -- Face Identification & Blockchain Verification

This repository contains the complete pipeline for the HH Goa 2026 Task 3 project:
Face Scan -> Web/Social Media Search -> Matching Post -> Blockchain Upload -> Verification.

## Project Structure

The codebase is organized into functional modules:

```text
|-- face/              # Face detection, recognition, and embeddings
|-- search/            # Reverse image search and social media scraping
|-- blockchain/        # Canonical data, SHA-256 fingerprinting, and Smart Contract verification
|-- data/              # Data storage (e.g., discovered_post.json, sample_post.json)
|-- tests/             # Unit and integration tests
|-- main.py            # End-to-end integration script tying everything together
|-- requirements.txt   # Python dependencies
|-- hardhat.config.js  # Local blockchain configuration
|-- .env.example       # Environment variables template
```

## Setup

1. **Python dependencies**
   ```bash
   py -m pip install -r requirements.txt
   ```

2. **Blockchain tooling (Hardhat)**
   ```bash
   npm install
   ```

3. **Environment setup**
   Copy `.env.example` to `.env` and fill in the values if connecting to a real network (e.g., Sepolia).
   For local testing, the default Anvil/Hardhat keys provided in `.env.example` are sufficient.

## Running the Pipeline (Local Development)

The complete pipeline can be tested locally using Hardhat to simulate an Ethereum blockchain.

1. **Start the local blockchain**
   Keep this running in a separate terminal:
   ```bash
   npx hardhat node
   ```

2. **Run the integration pipeline**
   The integration script loads discovery results, creates a deterministic fingerprint, deploys a fresh smart contract, uploads the fingerprint, and verifies it.
   ```bash
   py main.py data/sample_post.json
   ```

   Once the `face` and `search` modules generate actual results, they should be written to `data/discovered_post.json` and run via:
   ```bash
   py main.py data/discovered_post.json
   ```
   (Or simply `py main.py` as it defaults to `data/discovered_post.json`).

## Testing

The project includes an extensive test suite ensuring determinism, tamper-evidence, and smart contract functionality.

```bash
# Run all tests
py -m pytest tests/ -v

# Run only fingerprint generation tests
py -m pytest tests/test_hash_generator.py -v

# Run only blockchain and verification tests
py -m pytest tests/test_blockchain.py -v
```

## Blockchain Module Details

The `blockchain/` module ensures data integrity by converting discovered post data into a deterministic canonical format, hashing it (SHA-256), and storing it in a Solidity smart contract (`ContentVerifier`).

Key features:
- **Deterministic Hashing**: Dictionary ordering, JSON metadata fields, and whitespace are normalized.
- **Image Hashing**: Downloads or reads local image files and incorporates their SHA-256 hash. If unavailable, falls back gracefully.
- **Tamper Evidence**: Any modification to the URL, text, image, or metadata changes the hash and fails blockchain verification.
- **Minimal Smart Contract**: Open, auditable, and immutable record-keeping on-chain.
