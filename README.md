# SatoshiFi: Decentralized PoW Mining Pool Management

**The first decentralized solution for managing mining pools across all major PoW networks, built on Ethereum with federated coinbase addresses and independent custodians.**

## Overview

SatoshiFi addresses critical problems in traditional mining pools: lack of transparency, expensive withdrawals ($20-100 fees), and no DeFi access. Our solution provides:

- **85-95% withdrawal fee reduction** through privileged pool transactions
- **100% transparent operations** via Ethereum smart contracts
- **Automatic DeFi integration** for mining rewards
- **Independent custodian federation** with FROST threshold signatures
- **Multi-network support** (Bitcoin, Dogecoin, Bitcoin Cash, Litecoin)

## Key Innovations

### 🏦 Federated Coinbase Addresses
Mining pool coinbase addresses become TSS-controlled federated addresses. Block rewards automatically collateralize mp-tokens on Ethereum, eliminating trust dependencies.

### ⚡ Privileged Withdrawal System  
Miners queue withdrawals with guaranteed inclusion in the next pool block at minimal fees. Emergency CPFP mechanism available for urgent transactions.

### 🤝 Independent Custodian Federation
Professional custodians stake collateral and compete on transparent rates. 5-of-7 FROST threshold signatures ensure security without single points of failure.

## Architecture

```
┌─────────────────────────────────────────┐
│         Ethereum Smart Contracts       │
│  mp-Tokens │ S-Tokens │ Staking │ DEX  │
└─────────────────┬───────────────────────┘
                  │ FROST Protocol
┌─────────────────┴───────────────────────┐
│     Independent Custodian Federation    │  
│   5-of-7 Threshold Signature Security   │
└─────────────────┬───────────────────────┘
                  │ Federated Addresses
┌─────────────────┴───────────────────────┐
│       PoW Networks (Coinbase)          │
│ Bitcoin │ Dogecoin │ BCH │ Litecoin    │
└─────────────────────────────────────────┘
```

## Two-Level Token System

### Level 1: mp-Tokens (Pool-Specific Vouchers)
- Pool-specific withdrawal vouchers (mpBTC, mpDOGE, etc.)
- Guaranteed redemption through pool queues
- Minimal withdrawal fees via privileged transactions
- Automatic issuance when pools find blocks

### Level 2: S-Tokens (Custodial Wrapped Tokens)  
- Fungible wrapped tokens with full DeFi compatibility
- Cross-chain functionality between all supported networks
- Access to lending, staking, and yield farming
- Professional custody through independent operators

## Supported Networks

| Network | Token | Block Time | Current Reward | Status |
|---------|-------|------------|----------------|---------|
| Bitcoin | mpBTC → SBTC | ~10 min | 3.125 BTC | ✅ Ready |
| Dogecoin | mpDOGE → SDOGE | ~1 min | 10,000 DOGE | ✅ Ready |
| Bitcoin Cash | mpBCH → SBCH | ~10 min | 6.25 BCH | ✅ Ready |  
| Litecoin | mpLTC → SLTC | ~2.5 min | 12.5 LTC | ✅ Ready |

## Economic Model

### Fee Structure (Configurable)
- **Miners**: 96.75% (primary reward distribution)
- **Pool Operation**: 2.0% (infrastructure and management)
- **Protocol Development**: 0.5% (core development)
- **TSS Operators**: 0.75% (security infrastructure)

### Benefits Comparison

| Feature | Traditional Pools | SatoshiFi |
|---------|------------------|-----------|
| Withdrawal Fees | $20-100 | $1-5 |
| Transparency | Trust-based | Cryptographic |
| DeFi Access | None | Full integration |
| Single Point of Failure | Yes | No (5-of-7 TSS) |
| Cross-chain Support | Limited | Native |

## Technical Implementation

### FROST Protocol Integration
- Gas-efficient verification (~4200 gas per operation)
- 5-of-7 threshold signature configuration  
- On-chain verification through `frost-secp256k1-evm`
- Heartbeat mechanism prevents fund lockup

### Smart Contract Suite
- **Pool Coordinator**: Multi-chain pool coordination
- **TSS Manager**: Threshold signature group management  
- **mp-Token Contracts**: Pool-specific voucher system
- **S-Token Contracts**: DeFi-compatible wrapped tokens
- **SPV Verification**: Cross-chain transaction proofs

### Mining Pool Management
- Complete lifecycle from pool creation to reward distribution
- Support for Stratum v1 and v2 protocols
- Real-time share validation and analytics
- Multiple payout schemes (PPLNS, PPS, PPS+, PROP, SOLO)
- Enterprise-grade statistics and monitoring

## Security Analysis

### Trust Assumptions
- **Honest Majority**: >50% of TSS operators act honestly
- **Network Synchrony**: Synchronous network for critical operations
- **Cryptographic Security**: Discrete logarithm hardness in secp256k1
- **Liveness**: Threshold operators available for signing

### Threat Mitigation
- **Custodian Collusion**: Large stake requirements, reputation systems
- **Smart Contract Bugs**: Formal verification, audits, bug bounties  
- **Oracle Manipulation**: Time-weighted prices, multiple sources
- **Network Congestion**: Emergency mechanisms, L2 scaling

## Development Status

### Completed ✅
- FROST threshold signature integration
- Multi-chain SPV verification system
- Two-level token architecture (mp-tokens + S-tokens)
- Complete smart contract suite
- Mining pool management infrastructure
- Independent custodian federation design

### Integration Ready 🚀
- Bitcoin mainnet with Taproot support
- Ethereum mainnet smart contracts
- All target PoW networks verified
- DeFi protocol compatibility confirmed

## Getting Started

### For Mining Pool Operators
1. **Assessment**: Technical evaluation and compatibility analysis
2. **TSS Setup**: Custodian selection and FROST group configuration  
3. **Address Migration**: Transition to federated coinbase addresses
4. **Worker Migration**: Gradual miner transition to new infrastructure
5. **DeFi Activation**: Enable S-token functionality

### For Independent Custodians
1. **Collateral Staking**: Deposit required stake in target network
2. **Software Installation**: Run specialized FROST client
3. **Registration**: On-chain custodian registration process
4. **Rate Setting**: Configure competitive service rates
5. **Operations**: Participate in threshold signature operations

### For Miners
1. **Connect**: Use existing mining hardware with Stratum
2. **Earn**: Receive mp-tokens for block contributions
3. **Choose**: Keep mp-tokens or convert to S-tokens for DeFi
4. **Access**: Full access to staking, lending, and trading

## Repository Structure

```
├── contracts/           # Ethereum smart contracts
├── frost-client/        # TSS operator client software  
├── pool-manager/        # Mining pool management system
├── docs/               # Technical documentation
├── examples/           # Integration examples
└── tests/              # Comprehensive test suite
```

## Documentation

- **[Technical Whitepaper](https://unilayer.solutions/wp.html)**: Complete technical specification
- **[Integration Guide](https://unilayer.solutions/wp.html)**: Step-by-step implementation
- **[API Reference](coming soon)**: Complete API documentation
- **[Security Analysis](coming soon)**: Comprehensive security review

## Economic Impact

### For Miners
- 85-95% reduction in withdrawal fees
- Access to DeFi yields on mining rewards
- Transparent, verifiable pool operations
- Cross-chain functionality

### For Pool Operators  
- Reduced infrastructure complexity
- New revenue streams from DeFi integration
- Enhanced security through distributed model
- Competitive advantage through transparency

### For Custodians
- Independent business opportunity in growing crypto infrastructure
- Revenue from TSS operations and custody services
- Competitive marketplace with reputation-based selection

## Contributing

We welcome contributions from the community! Please see our [Contributing Guide](CONTRIBUTING.md) for details on:

- Code contribution process
- Development environment setup  
- Testing requirements
- Documentation standards

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contact

- **Email**: [sb@unilayer.solutions](mailto:sb@unilayer.solutions)
- **GitHub**: [https://github.com/SatoshiFi](https://github.com/SatoshiFi)
- **Documentation**: [Technical Whitepaper](https://unilayer.solutions/wp.html)

## Acknowledgments

- FROST protocol development by [Zcash Foundation](https://github.com/ZcashFoundation/frost)
- `frost-secp256k1-evm` integration for Ethereum compatibility
- Bitcoin Core, Dogecoin Core, Bitcoin Cash, and Litecoin development teams
- Ethereum Foundation for smart contract infrastructure

---

**SatoshiFi**: Transforming mining pool management through decentralization, transparency, and DeFi integration.
