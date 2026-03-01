# Capital One Fraud Detection System

## Overview

The Capital One Fraud Detection System is a cloud-based application designed to identify potentially fraudulent credit card transactions in real time. The system analyzes transaction data, generates a fraud risk score, and sends SMS alerts to users when suspicious activity exceeds a user-defined threshold. It is built to demonstrate how machine learning, cloud infrastructure, and event-driven services can work together to improve fraud detection and customer response time.

## Problem Statement

Credit card fraud can cause major financial losses for both customers and financial institutions. Traditional fraud detection systems may not always provide immediate alerts or allow users to respond quickly. This project aims to create a simple but effective fraud detection workflow that:

* processes transactions through an API,
* predicts the likelihood of fraud,
* notifies users immediately through text alerts,
* and allows user responses to improve fraud handling.

## Key Features

* **Transaction API** for creating and processing credit card transactions
* **Fraud scoring model** that classifies transactions as low-risk or suspicious
* **User-defined fraud threshold** so alerts are only sent when risk exceeds a chosen level
* **SMS alerts** to notify users of suspicious transactions in real time
* **Two-way user response flow** so users can confirm or deny fraudulent activity
* **Cloud deployment on AWS** for scalability and system integration
* **Simple UI** for account creation and transaction submission

## How It Works

1. A transaction is submitted through the application or API.
2. The backend sends the transaction data to the fraud detection model.
3. The model returns a fraud probability score.
4. If the score exceeds the user’s threshold, the system triggers an SMS alert.
5. The user can respond to the text alert to confirm whether the transaction is legitimate.
6. The system stores the response and can use that feedback to improve fraud labeling and future detection workflows.

## Tech Stack

* **Frontend:** Simple web UI
* **Backend:** API service for transaction handling
* **Machine Learning:** Fraud classification model
* **Messaging:** Twilio SMS alerts
* **Cloud:** AWS
* **Version Control:** Git / GitHub

## System Architecture

This project follows an event-driven architecture where transaction events flow through multiple connected services:

* Account creation / preferences service
* Transaction input layer / service
* Fraud scoring / model service
* Alerting service
* User response handling
* Cloud-hosted infrastructure

The full architecture and flow diagram is attached to the repository with specific details about the overall system. 

## Example Use Case

A customer makes a credit card purchase. The system evaluates the transaction and assigns a high fraud score. Because the score exceeds the customer’s chosen threshold, the system immediately sends an SMS alert. The customer replies to confirm whether the charge is legitimate, allowing the system to update the transaction status.

## API Endpoints

Example endpoints may include:

* `POST /transactions` – create and process a transaction
* `GET /transactions/:id` – retrieve transaction details
* `POST /alerts/respond` – process user response to fraud alert
* `GET /users/:id/settings` – retrieve user fraud threshold settings

## Future Improvements

* Improve model accuracy with more training data
* Add a dashboard for transaction history and fraud analytics
* Support push notifications in addition to SMS
* Add authentication and role-based access
* Store and use user feedback for ongoing model retraining
* Expand monitoring and logging for production deployment

## Project Goals

This project is intended to demonstrate:

* real-time fraud detection workflows,
* event-driven backend architecture,
* cloud integration,
* and user-centered alerting for suspicious financial activity.

## Team Poages Developers:

* Ricky Das
* Stanley White
* Swapnil Gore
* Anirudh Jagannath
* Jivesh Mehta
* Kyle Poage
