# SatoshiFi
A smart contract system for Bitcoin integration, providing dual staking functionality, mining pool management, trustless lending services, and hashrate tokenization.

## Project Description
SatoshiFi is a protocol designed to extend the capabilities of Rootstock (RSK) by providing additional functionality for interacting with Bitcoin transactions. The system leverages the existing Powpeg infrastructure to ensure reliable integration between the Bitcoin and RSK networks.

Key system components include:

-   **Protocol Core (SatoshiFiCore):** Provides the core logic for interacting with Powpeg, managing user identification, and processing transactions.
-   **SatFi Token (SatFiToken):** An ERC-20 compatible token featuring extended functionality.
-   **Dual Staking System:** A mechanism enabling users to stake both RBTC and SatFi tokens.
-   **Mining Pool Management:** Functionality for creating and managing mining pools.
-   **Reward Distribution System:** Handles the calculation and distribution of rewards.
-   **Trustless Lending Services:** A mechanism allowing users to borrow stablecoins using BTC as collateral, or borrow BTC using stablecoins as collateral.

## Solution Architecture
The system utilizes a modular architecture, with each component handling specific functionality:

-   **Core Protocol Contract:** Processes Peg-In and Peg-Out transactions leveraging the Powpeg interfaces (IBridge and IFederation).
-   **SatFi Token Contract:** Implements an ERC-20 compatible token supporting meta-transactions and configurable fees.
-   **Dual Staking Contract:** Manages the staking of RBTC and SatFi tokens.
-   **Mining Pool Manager:** Enables the creation and management of mining pools.
-   **Reward Distribution System:** Responsible for calculating and distributing rewards.
-   **Trustless Lending Services:** Responsible for accepting collateral, disbursing funds to borrowers, and liquidating collateral in case of margin call failures.

## Installation and Setup
### Requirements
-   Node.js v20.x or higher
-   npm v10.x or higher
-   Git

### Installation
1.  Clone the repository:
    ```bash
    git clone [https://github.com/SergeyBelets/SatFiPublic.git](https://github.com/SergeyBelets/SatFiPublic.git)
    cd SatoshiFi
    ```

2.  Install dependencies:
    ```bash
    npm install
    ```

3.  Create a `.env` file based on `.env.example`:
    ```bash
    cp .env.example .env
    ```

4.  Configure the required environment variables in the `.env` file.

### Testing
To run tests:
```bash
npx hardhat test
Deployment
To deploy to the Rootstock testnet:

Bash

npx hardhat run scripts/deployment/deploy.js --network rskTestnet
Powpeg Integration
The SatoshiFi system utilizes the Powpeg API for Bitcoin integration rather than duplicating its functionality. The Peg-In and Peg-Out processes work as follows:

Bitcoin Locking Process (Peg-In)
ID Binding:

The user registers their RSK address with the SatoshiFi contract.
The system generates a unique identifier intended for inclusion in the OP_RETURN field of the Bitcoin transaction.
Getting Instructions:

The contract retrieves the current federation address via the Powpeg API.
The user receives instructions to send BTC to the federation address, including the unique identifier in the OP_RETURN field.
Tracking and Verification:

The system monitors transactions to the federation address.
When a transaction arrives at the federation address containing the corresponding identifier in its OP_RETURN field, the system associates the pegged funds with the specific user's RSK address.
Bitcoin Unlocking Process (Peg-Out)
Initiating Unlock:

The user initiates a withdrawal request for their funds via the SatoshiFi interface.
The user specifies the recipient's destination BTC address.
Request Processing:

The contract verifies the user's permissions and available funds.
It calls the standard Powpeg method (createPegOut) to initiate the Peg-Out process.
The system records the association between this Peg-Out request and the user.
Status Tracking:

The system monitors the execution of the Peg-Out request.
It updates the status of the user's operation as the Peg-Out process progresses.
Project Structure
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
│   └── lending/               # Added based on description
│       └── TrustlessLending.sol # Added based on description
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
(Note: Added potential lending directory/contract based on description)

Powpeg Interfaces
IBridge
Solidity

interface IBridge {
    // Retrieves Peg-In transaction information
    function getPegInInfo(bytes32 btcTxHash) external view returns (
        bool processed,
        address receiver,
        uint256 amount
    );

    // Initiates a BTC unlock request (Peg-Out)
    function createPegOut(
        bytes20 btcDestinationAddress,
        uint256 amount
    ) external returns (bytes32 pegoutTxHash);
}
IFederation
Solidity

interface IFederation {
    // Retrieves the current federation BTC address
    function getFederationAddress() external view returns (bytes20);

    // Checks the federation status and Powpeg activity
    function isActive() external view returns (bool);
}
Dual Staking System
The dual staking system allows users to stake both RBTC and SatFi tokens and earn rewards. Key features:

Stake RBTC, SatFi, or both assets simultaneously.
Choose flexible locking periods ranging from 7 to 365 days.
Benefit from yield multipliers based on the chosen locking period.
Earn dynamic reward rates that can be adjusted.
Includes protection against reentrancy attacks.
Usage example:

Solidity

// Staking 0.1 RBTC and 100 SatFi for 30 days
dualStaking.stake{value: ethers.parseEther("0.1")}(
    ethers.parseUnits("100", 18),
    30 days // Assuming 'days' is defined or replaced with seconds
);

// Claiming accumulated rewards
dualStaking.claimReward();

// Unstaking after the locking period expires
dualStaking.unstake();
SatFi Token
The SatFi token is an ERC-20 compliant token with the following additional features:

Meta-transaction support: Enables gas-less transactions for users.
Dynamic Fees: A dynamic fee mechanism with configurable parameters.
Burnable: Tokens can be burned (destroyed).
Mintable: New tokens can be created (minted) by the contract owner.
Meta-transaction usage example:

TypeScript

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
    data: "0x" // Example data payload
};

const signature = await sender._signTypedData(domain, types, metaTx);

// Executing a meta-transaction via a relayer or the contract itself
await satFiToken.executeMetaTransaction(
    metaTx.from,
    metaTx.to,
    metaTx.value,
    metaTx.data,
    signature
);
Frontend
A web interface is planned for system interaction, utilizing the following technologies:

React.js or Vue.js for the user interface.
ethers.js for blockchain interaction.
Web3Modal for wallet connection.
Key interface components will include:

Wallet connection (e.g., MetaMask via Web3Modal).
Management of BTC address binding.
Staking interface.
Transaction monitoring.
Mining pool management interface.
Lending service interface.
Testing Recommendations
Utilize the Rootstock testnet to verify interactions with the live Powpeg system.
Develop mock contracts or emulators for Powpeg components to facilitate local testing.
Implement comprehensive unit tests covering all critical functions.
Create integration tests to ensure proper interaction between different system modules.
Perform thorough security testing and potentially a formal audit, especially for functions managing user funds.
Running the Local Development Environment
Bash

# Start a local Hardhat network instance
npx hardhat node

# Deploy contracts to the local network
npx hardhat run scripts/deployment/deploy.js --network localhost

# Run tests with code coverage report
npx hardhat coverage
Roadmap
Q1 2025: Develop and test core components

Implement protocol core
Develop SatFi token
Create dual staking system
Q2 2025: Expand functionality

Implement mining pool management
Develop reward distribution system
Implement trustless lending services
Integrate with Rootstock testnet
Q3 2025: Develop and test frontend

Create web interface
Conduct security audit
Launch beta version on testnet
Q4 2025: Mainnet launch

Deploy contracts to Rootstock mainnet
Launch marketing campaign
Initiate partnership programs with mining pools
License
MIT

Authors
Core smart contract development by:
@HelixJuke
@Chopper
Project management, requirements, and analytics by Sergey Belets (@SergeyBelets)