# SatoshiFi - Bitcoin Mining Pool Management Platform

## SatoshiFi Project

**SatoshiFi** is a decentralized platform built on Ethereum blockchain for Bitcoin mining pool management with integrated DeFi services. The platform provides bridge interaction between Bitcoin and Ethereum, offering users staking opportunities, worker management, and reward distribution.

### Key Features

- ** Mining Pool Management**: Worker creation, task distribution, performance monitoring
- ** Multi-asset Staking**: BTC, USDT, SatFi tokens with flexible lock conditions
- ** Bitcoin Bridge**: Secure interaction between Bitcoin and Ethereum
- ** Real-time Monitoring**: Track mining statistics and rewards in real-time
- ** Trustless Architecture**: Decentralized management without third parties

---

## System Architecture

### Infrastructure Components

```
┌─────────────────────────────────────────────────────────────────┐
│                    Ethereum (Sepolia Testnet)                  │
│  ┌─────────────────────────────────────────────────────────────┤
│  │ SatoshiFi Smart Contracts                                   │
│  │ ├── SatFiToken.sol (ERC-20)                                │
│  │ ├── MultiAssetStaking.sol                                  │
│  │ ├── MiningPoolManager.sol                                  │
│  │ ├── RewardDistribution.sol                                 │
│  │ └── MockTokens.sol (mockBTC, mockUSDT)                    │
│  └─────────────────────────────────────────────────────────────┤
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Frontend Interface                          │
│  https://unilayer.solutions/                                   │
│  ├── Wallet Connection (Web3Modal)                            │
│  ├── Staking Interface                                         │
│  ├── Mining Pool Dashboard                                     │
│  ├── Faucet for Test Tokens                                   │
│  └── Statistics & Monitoring                                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                Bitcoin Testnet Infrastructure                   │
│  ┌─────────────────────────────────────────────────────────────┤
│  │ AWS ECS Cluster (eu-north-1)                               │
│  │ ├── Coordinator Node (51.20.82.101)                       │
│  │ ├── Worker Pool A (nodes 0-4)                             │
│  │ ├── Worker Pool B (nodes 5-9)                             │
│  │ └── API Proxy (16.170.245.61)                             │
│  └─────────────────────────────────────────────────────────────┤
│  │ Network Status: regtest, 112 blocks, 500+ BTC             │
│  │ Real-time monitoring via btcscanner.html                   │
│  │ Wallet management via btcwallet.html                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## Technical Specifications

### Smart Contract Stack

#### SatFiToken (ERC-20)
```solidity
// Platform native token
contract SatFiToken {
    - Standard ERC-20 functionality
    - Mintable/Burnable capabilities
    - Gas-optimized operations
    - Staking contract integration
}
```

#### MultiAssetStaking
```solidity
// Multi-asset staking system
contract MultiAssetStaking {
    - Stake BTC, USDT, SatFi tokens
    - Flexible lock periods (7-365 days)
    - Dynamic reward rates
    - APY multipliers
    - Emergency withdrawal functions
}
```

#### MiningPoolManager
```solidity
// Mining pool management
contract MiningPoolManager {
    - Worker registration
    - Mining task creation
    - Performance tracking
    - Automatic reward distribution
}
```

### Bitcoin Testnet Infrastructure

**11 Bitcoin Core v29.0.0 nodes:**
- 1 Coordinator node (network coordination)
- 10 Worker nodes (mining pools A and B)
- Regtest mode for fast testing
- RPC API for Ethereum integration

**Current network statistics:**
- Block height: 112+ blocks
- Total BTC: 550+ BTC
- Network difficulty: minimal (regtest)
- Block time: 10 seconds (manual generation)

---

## Quick Start

### Prerequisites

```bash
Node.js v20.x+
npm v10.x+
MetaMask or compatible Web3 wallet
Git
```

### Installation and Setup

```bash
# 1. Clone repository
git clone https://github.com/SergeyBelets/SatFiPublic.git
cd SatoshiFi

# 2. Install dependencies
npm install

# 3. Environment configuration
cp .env.example .env
# Configure environment variables

# 4. Compile contracts
npx hardhat compile

# 5. Run tests
npx hardhat test

# 6. Deploy to Sepolia testnet
npx hardhat run scripts/deploy.js --network sepolia
```

### Frontend Setup

```bash
# Local development
npm run dev

# Production build
npm run build

# Start static server
npm run serve
```

---

## Platform Integration

### Ethereum Connection

```javascript
// Web3 integration
import { ethers } from 'ethers';
import { CONTRACT_ADDRESSES } from './config';

// Connect to Sepolia testnet
const provider = new ethers.JsonRpcProvider(process.env.SEPOLIA_RPC_URL);
const signer = await provider.getSigner();

// Initialize contracts
const satFiToken = new ethers.Contract(
    CONTRACT_ADDRESSES.SATFI_TOKEN,
    SatFiTokenABI,
    signer
);

const staking = new ethers.Contract(
    CONTRACT_ADDRESSES.STAKING,
    StakingABI,
    signer
);
```

### Staking Operations

```javascript
// Stake mockBTC
async function stakeBTC(amount, lockPeriod) {
    // Approve tokens
    await mockBTC.approve(stakingContract.address, amount);
    
    // Stake tokens
    const tx = await stakingContract.stakeBTC(amount, lockPeriod);
    await tx.wait();
    
    console.log('BTC staked successfully!');
}

// Claim rewards
async function claimRewards() {
    const tx = await stakingContract.claimRewards();
    await tx.wait();
    
    console.log('Rewards claimed!');
}
```

### Bitcoin Testnet Integration

```javascript
// Bitcoin RPC calls via API proxy
async function getBitcoinBalance(address) {
    const response = await fetch('https://api.unilayer.solutions/api/btc-proxy', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            node: 'coordinator',
            method: 'scantxoutset',
            params: ['start', [`addr(${address})`]]
        })
    });
    
    const data = await response.json();
    return data.result.total_amount;
}
```

---

## User Interface

### Main Screens

** Dashboard**
- Portfolio overview
- Active stakes
- Available rewards
- Mining pool performance

** Staking Interface**
- Multi-asset staking (BTC, USDT, SatFi)
- Flexible lock periods
- APY calculator
- Real-time rewards tracking

** Mining Pools**
- Worker registration
- Pool statistics
- Hashrate monitoring
- Reward distribution

** Faucet**
- Get test mockBTC tokens
- Get test mockUSDT tokens
- Daily limits and cooldowns

### Interactive Components

```jsx
// React staking component
function StakingInterface() {
    const [selectedAsset, setSelectedAsset] = useState('BTC');
    const [amount, setAmount] = useState('');
    const [lockPeriod, setLockPeriod] = useState(30);
    
    return (
        <div className="staking-interface">
            <AssetSelector onChange={setSelectedAsset} />
            <AmountInput value={amount} onChange={setAmount} />
            <LockPeriodSlider value={lockPeriod} onChange={setLockPeriod} />
            <StakeButton onClick={() => executeStake(selectedAsset, amount, lockPeriod)} />
        </div>
    );
}
```

---

## Testing

### Unit Tests

```bash
# Run all tests
npx hardhat test

# Test specific contract
npx hardhat test test/SatFiToken.test.js

# Coverage report
npx hardhat coverage
```

### Integration Tests

```bash
# Test Bitcoin integration
npm run test:bitcoin

# End-to-end testing
npm run test:e2e

# Performance testing
npm run test:performance
```

### Testnet Addresses

```yaml
Sepolia Testnet:
  SatFiToken: 0x[CONTRACT_ADDRESS]
  MultiAssetStaking: 0x[CONTRACT_ADDRESS]
  MockBTC: 0x[CONTRACT_ADDRESS]
  MockUSDT: 0x[CONTRACT_ADDRESS]
  MiningPoolManager: 0x[CONTRACT_ADDRESS]

Bitcoin Testnet:
  Coordinator Node: 51.20.82.101:8332
  API Proxy: https://api.unilayer.solutions/api/btc-proxy
  Frontend: https://unilayer.solutions/
```

---

## Monitoring and Analytics

### Real-time Metrics

**Bitcoin Network:**
- Block height and network status
- Node connectivity (11/11 online)
- Mempool transactions
- Mining statistics

**Ethereum Contracts:**
- Total Value Locked (TVL)
- Active stakes count
- Reward distribution
- Gas usage optimization

**Platform Performance:**
- API response times (150-500ms)
- Transaction success rates
- User activity metrics
- Error monitoring

### Dashboards

- **btcscanner.html**: Bitcoin network monitoring
- **btcwallet.html**: Bitcoin wallet management  
- **btcmanager.html**: Admin panel for Bitcoin nodes
- **Frontend dashboard**: Ethereum DeFi metrics

---

## Security

### Smart Contract Security

- **Reentrancy protection**: In all financial operations
- **Access control**: Role-based permissions
- **Input validation**: Comprehensive parameter checking  
- **Emergency functions**: Pause/unpause mechanisms
- **Audit ready**: Prepared for security audit

### Infrastructure Security

**Ethereum side:**
- Testnet environment isolation
- Multi-signature wallet integration (planned)
- Gas optimization for cost reduction

**Bitcoin side:**
- VPC isolation for testnet nodes
- RPC authentication
- EFS encryption at rest
- API proxy with HTTPS/TLS

---

## Roadmap

### Q1 2025 - Foundation
- ✅ Smart contract architecture
- ✅ Bitcoin testnet infrastructure  
- ✅ Basic staking functionality
- ✅ Mock token faucets
- ✅ Frontend MVP

### Q2 2025 - Enhancement
- 🔄 Mining pool integration
- 🔄 Advanced reward mechanisms
- 🔄 Cross-chain bridge optimization
- 🔄 Mobile-responsive UI
- 🔄 Security audit

### Q3 2025 - Scaling
- Mainnet deployment preparation
- Advanced analytics dashboard
- Partnership integrations
- Community governance features
- Performance optimization

### Q4 2025 - Launch
- Mainnet launch
- Marketing campaign
- Institutional partnerships
- Advanced DeFi features
- Global expansion

---

## Contributing

### For Developers

```bash
# Fork repository
git fork https://github.com/SergeyBelets/SatFiPublic.git

# Create feature branch
git checkout -b feature/new-feature

# Commit changes
git commit -m "Add new feature"

# Push and create PR
git push origin feature/new-feature
```

### Areas for Contribution

- **Smart Contract Development**: Solidity contracts and tests
- **Frontend Development**: React.js/Web3 integration
- **Bitcoin Integration**: RPC API and infrastructure
- **Documentation**: Technical docs and tutorials
- **Testing**: Unit/Integration tests
- **Security**: Audit and vulnerability research

---

## Support and Contacts

### Project Team

- **Project Lead & Analytics**: Sergey Belets (@SergeyBelets)
- **Smart Contract Development**: @HelixJuke, @Chopper  
- **Infrastructure & DevOps**: Core team
- **Community Management**: Telegram/Discord

### Contact

- **GitHub**: [SatoshiFi Repository](https://github.com/SergeyBelets/SatFiPublic)
- **Website**: [https://unilayer.solutions/](https://unilayer.solutions/)
- **Documentation**: [GitHub Wiki](https://github.com/SergeyBelets/SatFiPublic/wiki)
- **Issue Tracker**: [GitHub Issues](https://github.com/SergeyBelets/SatFiPublic/issues)

### Community

- **Telegram**: [SatoshiFi Community] (coming soon)
- **Discord**: [SatoshiFi Discord] (coming soon)
- **Twitter**: [@SatoshiFi] (coming soon)

---

## License

```
MIT License

Copyright (c) 2025 SatoshiFi Team

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
```

---

## Conclusion

SatoshiFi represents an innovative platform that combines the power of Bitcoin mining with the flexibility of Ethereum DeFi. Our architecture ensures secure and efficient interaction between two leading blockchain ecosystems, providing users with unique opportunities for earning and participating in decentralized finance.
