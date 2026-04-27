# Capital One Fraud Detection System

## Repository Link
https://github.com/sagore1263/CapitalOneCapstone

---

## Overview

The Capital One Fraud Detection System is a cloud-based application designed to identify potentially fraudulent credit card transactions in real time. The system analyzes transaction data, generates a fraud risk score, and sends WhatsApp alerts to users when suspicious activity exceeds a user-defined threshold.

This project demonstrates how cloud infrastructure, event-driven services, machine learning and user interaction can be combined to build a real-time, end-to-end fraud detection pipeline.

---

## Problem Statement

Credit card fraud can cause major financial losses for both customers and financial institutions. Traditional fraud detection systems may not always provide immediate alerts or allow users to respond quickly.

This project creates a system that:
- processes transactions through an API
- evaluates fraud risk
- notifies users instantly
- allows real-time user feedback

---

## Key Features

- Transaction API for creating and processing transactions  
- Random forest model based fraud scoring system   
- User-defined fraud threshold  
- Real-time WhatsApp alerts via Meta Cloud API  
- Two-way user response system (YES / NO)  
- Cloud deployment on AWS (Lambda, API Gateway, DynamoDB, IAM)  
- Fully serverless backend  
- Simple UI for creating users and transactions

---

## Setup Steps

### 1. Clone Repository
```bash
git clone https://github.com/sagore1263/CapitalOneCapstone
cd CapitalOneCapstone
```
### 2. Create user account 
```bash 
cd ui
npm run dev
```
Create a user account with your name, phone and card number and keep receiving alerts for fraud on your card as soon as it happens! 
---

### 2. AWS Setup

#### DynamoDB Tables

**users**
- Partition key: `cardNumber` (String)

**transactions**
- Partition key: `cardNumber` (String)
- Sort key: `transactionTimestamp` (String)

**pending_alerts**
- Partition key: `phoneNumber` (String)

---

#### Lambda Functions

- create_user: creates a new user in the corresponding table
- get_user: returns a json based on user id
- get_users: returns json of all users
- create_transaction: adds a transaction and calls fraud scoring service, checks if alert needs to be sent
- get_transaction: returns a transaction from the table based on id
- send_whatsapp_alert: sends a text alert to the phone number
- whatsapp_webhook: connects aws to meta api
- fraud scoring service: scores incoming transactions a value between 0 and 1.
---

#### Environment Variables

**create_transaction**
ALERT_LAMBDA_NAME=send_whatsapp_alert  
USERS_TABLE=users  
TRANSACTIONS_TABLE=transactions  

**send_whatsapp_alert**
META_ACCESS_TOKEN=your_token  
META_PHONE_NUMBER_ID=your_phone_id  
USERS_TABLE=users  
PENDING_ALERTS_TABLE=pending_alerts  

**whatsapp_webhook**
META_VERIFY_TOKEN=your_verify_token  
PENDING_ALERTS_TABLE=pending_alerts  
TRANSACTIONS_TABLE=transactions  

---

#### API Gateway

Set up the following routes:

POST /api/v1/users  
GET /api/v1/users  
GET /api/v1/users/{userId}  
POST /api/v1/users/{userId}/transactions  
GET /api/v1/transactions/{transactionId}  
GET /webhook  
POST /webhook  
---

### 3. WhatsApp Setup

- Add your number to Meta sandbox through our UI
- Webhook URL:
https://<api-id> (secret).execute-api.us-east-2.amazonaws.com/dev/webhook

---

## How It Works

1. A user is created with phone number, card number, and threshold.
2. A transaction is submitted via API.
3. The system assigns a fraud score between 0 and 1.
4. If fraud_score >= threshold, alert is triggered.
5. WhatsApp message is sent.
6. Pending alert stored in DynamoDB.
7. User replies YES or NO.
8. Webhook updates transaction status.

---

## What Works

- End-to-end API system  
- DynamoDB integration  
- Fraud detection pipeline  
- WhatsApp alert sending  
- User response loop  
- Serverless deployment  
- Every core feature we wanted to be done successfully works. 
---

## Limitations

- WhatsApp messages only   
- No authentication   
- No retry logic   

---

## Next Steps

- Real ML fraud model based on actual user data 
- Authentication    
- Fallback system 

---

## Docs

All relevants have been added to our team folder: https://drive.google.com/drive/u/0/folders/1DbgY-xU7hdEt7XRvP2AtdiWuC6pzbBLa

---

## Slides

https://docs.google.com/presentation/d/1lxFDlbs1Ii34p5SaSA63XaQNaf6mQjvTRTyobDehmQI/edit?slide=id.p#slide=id.p

---

## Team

Ricky Das  
Stanley White  
Swapnil Gore  
Anirudh Jagannath  
Jivesh Mehta  
Kyle Poage  
