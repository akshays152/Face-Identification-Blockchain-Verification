# RecallX — Blockchain Verification Module (Person 2)

## Overview

This module is **Person 2's** component of the HH Goa 2026 Task 3 project:
**Face Identification & Blockchain Verification**.

**Pipeline:**
```
Person 1: Face Scan -> Web/Social Media Search -> Matching Post
                                                       |
                                                       v
Person 2: Matching Post -> Canonical Data -> SHA-256 -> Smart Contract
           -> Blockchain Storage -> Retrieval -> Verification
```

Person 1 delivers their result as `person1/post_result.json`.
Person 2's module consumes it, fingerprints it, stores the fingerprint
on-chain, and verifies content integrity.

---

## Blockchain

**Target:** Ethereum-compatible chain.
- **Development:** Local Hardhat node (chain ID `31337`) — ships with the
  project, no testnet ETH needed.
- **Production:** Ethereum Sepolia testnet — just change `RPC_URL` and
  `CHAIN_ID` in `.env`.

**Why Hardhat locally?** Zero setup cost, deterministic test accounts with
10,000 ETH each, instant block mining, and no network dependency.

---

## Fingerprinting (SHA-256)

1. **Canonicalization** — the post data is normalised into a deterministic
   pipe-delimited string:
   ```
   url|image_hash|text|metadata_json
   ```
   - URL: stripped, lower-cased, trailing `/` removed.
   - Image: SHA-256 of the image bytes (local file or downloaded URL).
     If unavailable, the raw image reference is used as a fallback.
   - Text: stripped, inner whitespace collapsed.
   - Metadata: serialised as JSON with sorted keys and no extra whitespace.

2. **Hashing** — the canonical string is UTF-8 encoded and SHA-256 hashed.

3. **Guarantee** — identical input data always produces exactly the same
   64-character hex digest, regardless of Python dictionary ordering.

---

## Smart Contract (`ContentVerifier`)

Solidity `^0.8.20`, deployed on-chain. Stores:

| Field        | Type      | Description                          |
|--------------|-----------|--------------------------------------|
| `fingerprint`| `bytes32` | The SHA-256 hash (mapping key)       |
| `submitter`  | `address` | Ethereum address that stored it      |
| `timestamp`  | `uint256` | Block timestamp at storage time      |
| `exists`     | `bool`    | Whether the record exists            |

**Functions:**
- `storeHash(bytes32)` — store a fingerprint (reverts if duplicate).
- `verifyHash(bytes32)` — check if a fingerprint exists (view).
- `getRecord(bytes32)` — retrieve full record (view).

---

## Verification Logic

```
Current post data
      |  canonicalize
      v
SHA-256 fingerprint
      |  blockchain lookup
      v
Does this exact hash exist on-chain?
      |
  YES -> VERIFIED
  NO  -> NOT VERIFIED  (content was modified or never stored)
```

The tamper-evident property: if even one character of the post data changes,
the SHA-256 changes, and the lookup returns `false`.

---

## Setup

### Prerequisites
- Python 3.11+
- Node.js 18+ (for Hardhat)

### Installation

```bash
# Clone the repository
cd RecallX

# Install Python dependencies
py -m pip install -r person2/requirements.txt

# Install Hardhat (local blockchain)
npm install
```

### Configuration

```bash
# Copy the example env file
copy .env.example .env

# The defaults work for local Hardhat development.
# For Sepolia, edit RPC_URL, PRIVATE_KEY, and CHAIN_ID.
```

> **Security:** Never commit `.env`. Never use a mainnet key with real funds.

---

## Running

### 1. Start the local blockchain
```bash
npx hardhat node
```
Leave this running in a separate terminal.

### 2. Deploy the contract
```bash
py person2/deploy.py
```
This compiles the Solidity contract, deploys it, and prints the address.

### 3. Run the full pipeline
```bash
# With the sample test data
py integration/main.py person2/sample_post_result.json

# With Person 1's real output
py integration/main.py person1/post_result.json

# Default (tries person1/post_result.json, falls back to sample)
py integration/main.py
```

---

## Testing

```bash
# Start the local blockchain first
npx hardhat node

# Run all tests
py -m pytest person2/tests/ -v

# Run only hash generator tests (no blockchain needed)
py -m pytest person2/tests/test_hash_generator.py -v

# Run blockchain + verification tests (requires running node)
py -m pytest person2/tests/test_blockchain.py -v
```

**Test coverage:**
- 20 hash generator tests (determinism, sensitivity, edge cases, images)
- 13 blockchain tests (storage, retrieval, verification, tampering, missing records)
- **33 total, all passing**

---

## Project Structure

```
RecallX/
|-- person1/
|   |-- post_result.json          # Person 1's output (placeholder)
|
|-- person2/
|   |-- __init__.py
|   |-- config.py                 # Environment variable loader
|   |-- hash_generator.py         # SHA-256 fingerprinting
|   |-- contract.sol              # Solidity smart contract
|   |-- blockchain.py             # Web3 blockchain interface
|   |-- deploy.py                 # Contract deployment script
|   |-- verifier.py               # Verification logic
|   |-- sample_post_result.json   # Dev/test sample data
|   |-- requirements.txt          # Python dependencies
|   |-- tests/
|       |-- test_hash_generator.py
|       |-- test_blockchain.py
|
|-- integration/
|   |-- main.py                   # End-to-end pipeline
|
|-- .env.example                  # Environment template
|-- .gitignore
|-- hardhat.config.js             # Local blockchain config
|-- package.json                  # Hardhat dependency
|-- README.md                     # This file
```

---

## Integration Instructions for Person 1

1. Write your discovery results to `person1/post_result.json`:
   ```json
   {
     "post_url": "https://...",
     "post_image": "path/or/url",
     "post_text": "...",
     "metadata": { ... },
     "similarity": 0.92
   }
   ```

2. Run the pipeline:
   ```bash
   py integration/main.py
   ```

3. No changes to Person 2's code are needed. The module accepts
   any JSON object with the fields above.

---

## Limitations

| Area | Limitation |
|------|-----------|
| Image availability | If the image URL is inaccessible (404, auth-required, rate-limited), the image bytes cannot be hashed. The system handles this gracefully but the fingerprint will differ if the image later becomes available. |
| Metadata changes | If the source platform changes metadata (timestamps, view counts), the fingerprint will change. Only include stable metadata. |
| Testnet availability | Sepolia may have downtime or faucet limits. The local Hardhat node has no such constraints. |
| Gas costs | On a public testnet, each `storeHash` costs gas. On local Hardhat, gas is free. |
| Contract upgrades | The contract is immutable once deployed. Re-deploy for a new contract. |
| Single-store | Each fingerprint can only be stored once (by design, to prevent overwrites). |

---

## Security

- `.env` is in `.gitignore` — never committed.
- Private keys are never printed or logged.
- The `.env.example` uses Hardhat's publicly-known test keys only.
- No real funds or mainnet keys are used.
