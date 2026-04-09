Stock Trading Training System

This repository contains a 3-tier client-server application designed to train stockbrokers through a simulated market environment. The system features a custom price engine, administrative controls, and a secure cloud-native architecture.

System Architecture

The project utilizes a 3-tier logical structure to ensure separation of concerns and data security:

1. Presentation Tier (Frontend): A web-based GUI built with HTML, CSS, and JavaScript. It provides real-time market visualization, portfolio management, and administrative dashboards.
2. Application Tier (Business Logic): A Python Flask server hosted on AWS EC2. It processes trade requests, enforces market schedules, and runs the stochastic price generator.
3. Data Tier (Backend): A MySQL database on AWS RDS. It is isolated in a private subnet and stores all user profiles, ledger entries, and system audit logs.

Core Features

Customer Functionality
* Account Management: User registration and secure authentication.
* Trading: Buy and sell stocks at current market prices with an optional cancellation window before execution.
* Portfolio Tracking: Real-time view of stock holdings, cash balances, and full transaction history.
* Cash Management: Dedicated cash account for deposits and withdrawals; all sales proceeds are automatically settled here.

Administrator Functionality
* Market Orchestration: Create new stocks by defining ticker symbols, volume, and initial pricing.
* Temporal Controls: Set specific market hours and manage the trading calendar (weekdays and holiday closures).
* System Monitoring: Oversight of all market activity and security-related timestamps.

Trading Engine & GUI

The system incorporates a Random Stock Price Generator that simulates intraday volatility, ensuring prices fluctuate gradually rather than making erratic jumps. 

The GUI displays essential market metrics, including:
* Market Capitalization: Calculated as $Market\ Cap = Volume \times Price$.
* Daily Performance: Tracking of daily opening prices, highs, and lows.
* Asset Table: Real-time ticker symbols, current pricing, and circulating volume.

Technical Specifications
* Language: Python
* Web Framework: Flask
* Database: MySQL
* Infrastructure: AWS (EC2, RDS, VPC)
* Database Port: 3306 (Internal access only)
