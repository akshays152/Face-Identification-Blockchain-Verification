// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title  ContentVerifier
 * @notice Stores SHA-256 fingerprints of social/web post data on-chain
 *         and provides tamper-evident verification.
 *
 * Design goals
 * ------------
 *  - Minimal — only store, check, and retrieve.
 *  - Auditable — every function is commented.
 *  - No admin roles — anyone can store; anyone can verify.
 */
contract ContentVerifier {

    // -- Data --

    /// @notice On-chain record for a single fingerprint.
    struct Record {
        address submitter;   // who submitted the fingerprint
        uint256 timestamp;   // block.timestamp at submission
        bool    exists;      // true once stored
    }

    /// @notice Maps a SHA-256 fingerprint (as bytes32) to its record.
    mapping(bytes32 => Record) private records;

    // -- Events --

    /// @notice Emitted when a new fingerprint is stored.
    event HashStored(
        bytes32 indexed fingerprint,
        address indexed submitter,
        uint256 timestamp
    );

    // -- Write --

    /**
     * @notice Store a SHA-256 fingerprint on-chain.
     * @param  _hash  The 32-byte fingerprint to store.
     * @dev    Reverts if the fingerprint has already been stored
     *         (prevents accidental overwrites).
     */
    function storeHash(bytes32 _hash) external {
        require(!records[_hash].exists, "Fingerprint already stored");

        records[_hash] = Record({
            submitter: msg.sender,
            timestamp: block.timestamp,
            exists:    true
        });

        emit HashStored(_hash, msg.sender, block.timestamp);
    }

    // -- Read --

    /**
     * @notice Check whether a fingerprint exists on-chain.
     * @param  _hash  The 32-byte fingerprint to look up.
     * @return True if the fingerprint has been stored.
     */
    function verifyHash(bytes32 _hash) external view returns (bool) {
        return records[_hash].exists;
    }

    /**
     * @notice Retrieve the full record for a fingerprint.
     * @param  _hash  The 32-byte fingerprint.
     * @return submitter  Address that stored the fingerprint.
     * @return timestamp  Block timestamp of the storage transaction.
     * @return exists     Whether the record exists.
     */
    function getRecord(bytes32 _hash)
        external
        view
        returns (address submitter, uint256 timestamp, bool exists)
    {
        Record storage r = records[_hash];
        return (r.submitter, r.timestamp, r.exists);
    }
}
