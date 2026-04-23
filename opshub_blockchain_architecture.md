# OpsHub SMB Blockchain Module Architecture

## Overview

This document describes the blockchain integration module of the SMB-One
Stop (OpsHub) platform. The system integrates a Hardhat-based smart
contract layer with a Node.js backend and a Python escrow simulation
service. The goal is to provide blockchain-backed auditability for
business transactions and escrow settlements while keeping real payments
in INR through Razorpay.

------------------------------------------------------------------------

# System Architecture

## High Level Flow

User (SMB Platform) → Node Backend (Auth + Wallet Mapping) → Escrow
Service (Python) → Blockchain (Hardhat contracts) → PostgreSQL (metadata
storage)

Blockchain acts as a **proof and audit layer**, not a payment processor.

------------------------------------------------------------------------

# Technology Stack

## Blockchain Layer

-   Solidity
-   Hardhat
-   Ethers.js
-   Sepolia Testnet
-   MetaMask (server wallet)

## Backend

-   Node.js
-   Express
-   PostgreSQL
-   JWT Authentication
-   Ethers.js

## Escrow Simulation

-   Python FastAPI
-   Internal escrow contract simulation

## Payment Layer

-   Razorpay (INR payments)

------------------------------------------------------------------------

# Smart Contracts

## BusinessRegistry.sol

Purpose: Maintains blockchain identity of SMB businesses.

Functions: - registerBusiness(address owner, string name) -
getBusiness(address) - businessExists(address)

Role: Identity layer.

------------------------------------------------------------------------

## TransactionLedger.sol

Purpose: Stores verified financial transactions as blockchain proof.

Key Design: Stores only hashes of payment metadata. Full data stored
off-chain.

Structure:

Transaction: - id - from - to - amount - razorpayPaymentId -
metadataHash - timestamp

Functions: - recordTransaction() - getTransaction() -
getBusinessTransactions()

Role: Financial proof ledger.

------------------------------------------------------------------------

## EscrowRegistry.sol

Purpose: Stores escrow lifecycle proofs.

EscrowDeal: - id - escrowId - buyer - seller - amount - status -
metadataHash - timestamp

Functions: - recordEscrow() - completeEscrow() - getEscrow()

Role: Escrow lifecycle registry.

------------------------------------------------------------------------

# Backend Architecture

## Services Layer

### AuthService

Handles login authentication using SHA256 password comparison.

### UserService

Database operations: - find user - enable blockchain - wallet mapping

### WalletService

Creates custodial wallets. Encrypts private keys.

### BlockchainService

Handles: - Provider connection - Contract interaction - Server wallet
signing

### TransactionService

Records payment proofs on blockchain.

### EscrowService

Handles orchestration:

Create Flow: Node → Python escrow → Blockchain record → DB mapping

Completion Flow: Node → Python release → TransactionLedger record →
EscrowRegistry update

### PaymentService

Handles Razorpay webhook integration.

------------------------------------------------------------------------

# Database Design

## Users Table

Fields added: - wallet_address - wallet_private_key (encrypted) -
blockchain_enabled - blockchain_tx

## Payments Table

Stores: - Razorpay payment ID - wallets involved - blockchain hash -
metadata hash - full JSON

## Escrow Contracts Table

Stores: - escrow_id - buyer_wallet - seller_wallet - amount -
blockchain_deal_id - status

------------------------------------------------------------------------

# Escrow Lifecycle

## Creation

Buyer initiates deal → Python escrow locks funds → Blockchain
EscrowRegistry record → DB mapping stored

## Completion

Conditions met → Python releases funds → TransactionLedger record
created → EscrowRegistry updated → DB updated

------------------------------------------------------------------------

# Security Model

## Custodial Wallet Architecture

Users do not manage wallets.

System: Creates wallet Encrypts key Stores mapping Signs transactions
server-side

Benefits: Better UX Enterprise pattern No crypto knowledge required

------------------------------------------------------------------------

# Data Storage Strategy

## Off-chain Storage

PostgreSQL stores: Payment JSON Escrow data User data

## On-chain Storage

Blockchain stores: Hashes Proof references Status markers

Pattern: Off-chain storage + On-chain verification.

------------------------------------------------------------------------

# Transaction Recording Model

Razorpay Payment → Backend verification → SHA256 metadata hash →
Blockchain record

Guarantees: Immutability Auditability Fraud resistance

------------------------------------------------------------------------

# Escrow Integration Model

Python escrow manages: Fund locking Fund release Contract conditions

Blockchain records: Lifecycle proof Settlement proof

Node orchestrates both.

------------------------------------------------------------------------

# Key Design Decisions

Blockchain is not used for: Payments Wallet balances Token transfers

Blockchain is used for: Proof Audit Integrity Traceability

This aligns with enterprise blockchain practices.

------------------------------------------------------------------------

# Deployment Components

## Hardhat Project

Contains: contracts/ ignition/ test/ hardhat.config.js

Deploy using:

npx hardhat ignition deploy

------------------------------------------------------------------------

## Node Backend

Contains:

services/ routes/ config/ server.js

Runs: node src/server.js

------------------------------------------------------------------------

## Escrow Server

Python FastAPI service.

Handles escrow simulation.

------------------------------------------------------------------------

# Deliverables Summary

Completed:

BusinessRegistry contract TransactionLedger contract EscrowRegistry
contract Wallet onboarding Blockchain integration Escrow orchestration
Payment proof storage

This constitutes a complete SMB blockchain integration module.

------------------------------------------------------------------------

# Future Enhancements

Possible improvements:

Event listeners Admin audit dashboard Escrow webhook sync Document hash
verification Role based access

------------------------------------------------------------------------

# Conclusion

This architecture demonstrates a hybrid Web2-Web3 enterprise design
combining:

Traditional payments Blockchain verification Escrow orchestration Secure
identity mapping

The result is a scalable blockchain-backed SMB financial infrastructure.
