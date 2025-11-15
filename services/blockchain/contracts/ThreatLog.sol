// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

contract ThreatLog {
    
    struct Threat {
        uint id;
        address logger;
        string userIdHash;
        string attackType;
        uint timestamp;
    }
    
    mapping(uint => Threat) public threats;
    uint public threatCount;

    event ThreatLogged(
        uint id,
        address indexed logger,
        string userIdHash,
        string attackType,
        uint timestamp
    );

    function logThreat(string memory _userIdHash, string memory _attackType) public {
        threatCount++;
        
        threats[threatCount] = Threat(
            threatCount,
            msg.sender,
            _userIdHash,
            _attackType,
            block.timestamp
        );
        
        emit ThreatLogged(
            threatCount,
            msg.sender,
            _userIdHash,
            _attackType,
            block.timestamp
        );
    }
}
