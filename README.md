# HH Goa 2026 – Task 3: Face Identification & Blockchain Verification

A decentralized, tamper-evident media verification pipeline connecting biometric face recognition and genuine open-web/social candidate discovery with on-chain Ethereum smart contract attestation.

**Pipeline Flow:**
`Face Scan → Web/Social Media Search → Matching Post → Blockchain Upload → Verification`

---

## 1. 2-Person Work Division & Architecture

| Task Component | Responsible Role | Implementation Modules |
| :--- | :--- | :--- |
| **Face Detection** | Part 1 | `part1/face_detection.py` |
| **Face Embedding** | Part 1 | `part1/face_embedding.py` |
| **Genuine Web/Social Search** | Part 1 | `part1/web_search.py` |
| **Candidate Post Extraction** | Part 1 | `part1/post_extractor.py` |
| **Face Matching & Scoring** | Part 1 | `part1/face_matching.py` |
| **Handoff JSON Output** | Part 1 | `part1/post_result.json` |
| **Post Fingerprinting & SHA-256** | Part 2 | `part2/hash_generator.py` |
| **Smart Contract (Solidity)** | Part 2 | `part2/contract.sol` |
| **Contract Deployment** | Part 2 | `part2/deploy.py` |
| **Blockchain Client (Web3)** | Part 2 | `part2/blockchain.py` |
| **On-Chain Verification** | Part 2 | `part2/verifier.py` |
| **End-to-End Integration** | Both | `integration/main.py` |

The only coupling between Part 1 and Part 2 is the fixed JSON interface: `part1/post_result.json`.

---

## 2. Fixed Handoff Interface (`part1/post_result.json`)

Part 1 discovers and matches candidate posts, outputting canonical JSON:

```json
{
    "post_url": "https://social-network.io/verified/identity-post-9842",
    "post_image": "data/sample_face.jpg",
    "post_text": "Official verified user profile and identity post.",
    "metadata": {
        "platform": "social_network",
        "verified_badge": true,
        "timestamp": "1788793978"
    },
    "similarity": 0.917
}
```

---

## 3. Technology Stack

### Face Recognition & Embedding (Part 1)
- **Face Detection**: Neural **YuNet** detector (`cv2.FaceDetectorYN`) with 5-point facial landmark alignment.
- **Face Recognition**: Neural **SFace** (`cv2.FaceRecognizerSF`), generating 128-dimensional $L_2$-normalized feature vectors.
- **Matching Metric**: Cosine similarity $S_C(u, v) = \frac{u \cdot v}{\|u\| \|v\|}$ scaled to $[0.0, 1.0]$.
- Zero heavy C++ build dependencies like `dlib`; runs natively on Windows Python 3.13.

### Genuine Web Search (Part 1)
- **Live Search**: Live queries to Wikipedia/Wikimedia open-web search and Reddit public API endpoints.
- **No Hardcoded Data**: Dynamically discovers candidate posts containing page titles, content extracts, and full-resolution photograph URLs.
- **Caching**: Automated HTTP download, caching, and cryptographic verification of candidate images in `data/cache/`.

### Blockchain & Cryptographic Verification (Part 2)
- **Fingerprint Engine**: Canonical pipe-delimited normalization (`url | image_sha256 | text | sorted_metadata_json`) hashed via **SHA-256**.
- **Smart Contract**: Solidity `ContentVerifier.sol` deployed on Ethereum (EVM).
- **Web3 Connector**: Python `web3.py` client with automatic fallback simulation if local node is offline.

---

## 4. Installation & Setup

### 1. Python Environment
```bash
py -m pip install -r requirements.txt
```

### 2. Download Models
```bash
py download_models.py
```

### 3. Environment Configuration
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Default parameters are pre-configured for local development (RPC `http://127.0.0.1:8545`, Chain ID `31337`).

---

## 5. Running the Pipeline

### Option A: Complete End-to-End Integrated Pipeline
Executes the full 7-step pipeline from input image to blockchain verification:
```bash
py integration/main.py data/sample_face.jpg
```

**Expected Program Output:**
```text
========================================
FACE IDENTIFICATION & BLOCKCHAIN
========================================
[1] Loading face image...
[✓] Face detected
[2] Generating face embedding...
[✓] Embedding generated
[3] Searching web/social media...
[✓] Search completed
[4] Finding matching post...
[✓] Matching post found
Similarity: 91.7%
[5] Creating fingerprint...
[✓] SHA-256 generated
[6] Uploading to blockchain...
[✓] Transaction confirmed
[7] Verifying...
[✓] Hash matches blockchain
========================================
VERIFIED ✓
========================================
```

### Option B: Part 1 Independent Execution
Run Part 1 modules independently to test face identification and generate `part1/post_result.json`:

```bash
# Step 3: Face Detection
py part1/face_detection.py data/sample_face.jpg

# Step 3: Face Embedding
py part1/face_embedding.py data/sample_face.jpg

# Step 4: Web Search
py part1/web_search.py "portrait face"

# Step 5: Candidate Extraction
py part1/post_extractor.py

# Step 6 & 7: Matching & Handoff Creation
py part1/face_matching.py data/sample_face.jpg
```

### Option C: Part 2 Independent Execution
Run Part 2 modules independently on the handoff file:

```bash
# Generate SHA-256 fingerprint from Part 1's handoff JSON
py part2/hash_generator.py part1/post_result.json

# Run Blockchain Verification against node
py main.py part1/post_result.json
```

---

## 6. Testing

The repository contains a full test suite covering both Part 1 and Part 2 modules:

```bash
# Run all unit and integration tests
py -m pytest tests/ -v

# Run Part 1 tests (Detection, Embedding, Search, Matching, Extraction)
py -m pytest tests/test_part1.py -v

# Run Part 2 fingerprint determinism & tampering tests
py -m pytest tests/test_hash_generator.py -v
```
