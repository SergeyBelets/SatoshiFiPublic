# SatoshiFi
A smart contract system for Bitcoin and Rootstock integration, providing dual staking functionality, mining pool management, and hashrate tokenization.

## Project Description
SatoshiFi is a protocol that extends Rootstock (RSK) capabilities by adding additional functionality for working with Bitcoin transactions. The system uses the existing Powpeg infrastructure to ensure reliable integration between Bitcoin and RSK.

Main system components:

- Protocol Core (SatoshiFiCore) - provides the main logic for interacting with Powpeg, user identification, and transaction processing
- SatFi Token (SatFiToken) - ERC-20 compatible token with extended functionality
- Dual Staking System - mechanism for staking both RBTC and SatFi tokens
- Mining Pool Management - functionality for creating and managing mining pools
- Reward Distribution System - mechanisms for calculating and distributing rewards

## Solution Architecture
The system is built using a modular architecture, where each component is responsible for specific functionality:

- Core Protocol Contract processes Peg-In and Peg-Out transactions using Powpeg interfaces (IBridge and IFederation)
- SatFi Token Contract implements an ERC-20 compatible token with support for meta-transactions and fees
- Dual Staking Contract manages staking of RBTC and SatFi tokens
- Mining Pool Manager enables creation and management of pools
- Reward Distribution System is responsible for calculating and distributing rewards

## Installation and Setup
### Requirements
- Node.js v20.x or higher
- npm v10.x or higher
- Git

### Installation
1. Clone the repository:
```bash
git clone https://github.com/SergeyBelets/SatFiPublic.git
cd SatoshiFi
```

2. Install dependencies:
```bash
npm install
```

3. Create .env file based on .env.example:
```bash
cp .env.example .env
```

4. Configure environment variables in the .env file

### Testing
Run tests:
```bash
npx hardhat test
```

### Deployment
Deploy to Rootstock testnet:
```bash
npx hardhat run scripts/deployment/deploy.js --network rskTestnet
```

## Powpeg Integration
The SatoshiFi system does not duplicate Powpeg functionality but uses its API for Bitcoin integration. The Peg-In and Peg-Out processes work as follows:

### Bitcoin Locking Process (Peg-In)
1. **ID Binding**:
   - User registers their RSK address in the SatoshiFi contract
   - The system generates a unique identifier to be included in OP_RETURN

2. **Getting Instructions**:
   - The contract requests the current federation address through the Powpeg API
   - User receives instructions for sending BTC with the identifier added to OP_RETURN

3. **Tracking and Verification**:
   - The system monitors transactions to the federation address
   - When a transaction with the corresponding identifier in OP_RETURN is detected, the system binds the pegged funds to the specific user

### Bitcoin Unlocking Process (Peg-Out)
1. **Initiating Unlock**:
   - User requests withdrawal of funds through the SatoshiFi interface
   - Specifies the recipient's BTC address

2. **Request Processing**:
   - The contract verifies user rights and funds availability
   - Calls the standard Powpeg method to request Peg-Out (createPegOut)
   - Saves the association between the Peg-Out request and the user

3. **Status Tracking**:
   - The system monitors the execution of the Peg-Out request
   - Updates the user operation status as the process progresses

## Project Structure
```
SatoshiFi/
├── contracts/
│   ├── core/
│   │   └── SatoshiFiCore.sol
│   ├── token/
│   │   └── SatFiToken.sol
│   ├── staking/
│   │   └── DualStaking.sol
│   ├── pools/
│   │   └── MiningPoolManager.sol
│   └── rewards/
│       └── RewardDistribution.sol
├── scripts/
│   └── deployment/
│       └── deploy.js
├── test/
│   ├── SatoshiFiCore.test.js
│   ├── SatFiToken.test.js
│   └── integration/
├── .env
├── .env.example
├── .gitignore
├── hardhat.config.js
└── README.md
```

## Powpeg Interfaces
### IBridge
```solidity
interface IBridge {
    // Getting Peg-In transaction information
    function getPegInInfo(bytes32 btcTxHash) external view returns (
        bool processed,
        address receiver,
        uint256 amount
    );
    
    // Request for BTC unlocking (Peg-Out)
    function createPegOut(
        bytes20 btcDestinationAddress,
        uint256 amount
    ) external returns (bytes32 pegoutTxHash);
}
```

### IFederation
```solidity
interface IFederation {
    // Getting the current federation BTC address
    function getFederationAddress() external view returns (bytes20);
    
    // Checking federation status and Powpeg activity
    function isActive() external view returns (bool);
}
```

## Dual Staking System
The dual staking system allows users to stake both RBTC and SatFi tokens, receiving rewards for this. Main features:

- Ability to stake RBTC, SatFi, or both assets simultaneously
- Flexible locking periods from 7 to 365 days
- Yield multipliers depending on the locking period
- Dynamic reward rates with adjustment capability
- Protection against reentrancy attacks

Usage example:
```solidity
// Staking 0.1 RBTC and 100 SatFi for 30 days
dualStaking.stake{value: ethers.parseEther("0.1")}(
    ethers.parseUnits("100", 18),
    30 days
);

// Claiming accumulated rewards
dualStaking.claimReward();

// Unstaking after the locking period expires
dualStaking.unstake();
```

## SatFi Token
The SatFi token implements the ERC-20 standard with additional functionality:

- Support for meta-transactions for fee-less operations
- Dynamic fee mechanism with configuration options
- Token burning system (burnability)
- Ability to create new tokens by the contract owner

Example of using meta-transactions:
```typescript
// Signing a meta-transaction
const domain = {
    name: "SatoshiFi Token",
    version: "1",
    chainId: network.chainId,
    verifyingContract: satFiToken.address
};

const types = {
    MetaTransaction: [
        { name: "from", type: "address" },
        { name: "to", type: "address" },
        { name: "value", type: "uint256" },
        { name: "nonce", type: "uint256" },
        { name: "data", type: "bytes" }
    ]
};

const metaTx = {
    from: sender.address,
    to: recipient.address,
    value: ethers.parseUnits("10", 18),
    nonce: await satFiToken.getNonce(sender.address),
    data: "0x"
};

const signature = await sender._signTypedData(domain, types, metaTx);

// Executing a meta-transaction
await satFiToken.executeMetaTransaction(
    metaTx.from,
    metaTx.to,
    metaTx.value,
    metaTx.data,
    signature
);
```

## Frontend
A web interface will be developed for interacting with the system using the following technologies:

- React.js or Vue.js for the frontend
- ethers.js for blockchain interaction
- Web3Modal for wallet connection

Main interface components:
- Wallet connection (MetaMask)
- BTC address binding management
- Staking interface
- Transaction monitoring
- Mining pool management

## Testing Recommendations
1. Use Rootstock testnet to verify interaction with Powpeg
2. Create Powpeg component emulators for local testing
3. Write unit tests for all key functions
4. Prepare integration tests to verify module interaction
5. Conduct security testing for functions related to fund management

## Running the Local Development Environment
```bash
# Start local Hardhat network
npx hardhat node

# Deploy contracts to local network
npx hardhat run scripts/deployment/deploy.js --network localhost

# Run tests with code coverage
npx hardhat coverage
```

## Roadmap
1. **Q1 2025**: Development and testing of basic components
   - Implementation of the protocol core
   - Development of the SatFi token
   - Creation of the dual staking system

2. **Q2 2025**: Functionality expansion
   - Implementation of mining pool management
   - Development of the reward distribution system
   - Integration with Rootstock testnet

3. **Q3 2025**: Frontend development and testing
   - Creation of web interface
   - Security audit
   - Beta version launch in testnet

4. **Q4 2025**: Mainnet launch
   - Contract deployment to Rootstock mainnet
   - Marketing campaign launch
   - Start of partnership programs with mining pools

## License
MIT

## Authors
Original code was developed by:
- @HelixJuke
- @Chopper

English translation and project organization by Sergey Belets ([@SergeyBelets](https://github.com/SergeyBelets))