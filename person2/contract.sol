// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title  ContentVerifier
 * @notice Stores SHA-256 fingerprints of social/web post data on-chain
 *         and provides tamper-evident verification.
 */
contract ContentVerifier {

    struct Record {
        address submitter;
        uint256 timestamp;
        bool    exists;
    }

    mapping(bytes32 => Record) private records;

    event HashStored(
        bytes32 indexed fingerprint,
        address indexed submitter,
        uint256 timestamp
    );

    function storeHash(bytes32 _hash) external {
        require(!records[_hash].exists, "Fingerprint already stored");

        records[_hash] = Record({
            submitter: msg.sender,
            timestamp: block.timestamp,
            exists:    true
        });

        emit HashStored(_hash, msg.sender, block.timestamp);
    }

    function verifyHash(bytes32 _hash) external view returns (bool) {
        return records[_hash].exists;
    }

    function getRecord(bytes32 _hash)
        external
        view
        returns (address submitter, uint256 timestamp, bool exists)
    {
        Record storage r = records[_hash];
        return (r.submitter, r.timestamp, r.exists);
    }
}
