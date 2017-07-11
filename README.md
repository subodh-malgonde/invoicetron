## Info
This repo contains the code for the hackathon - https://awschatbot2017.devpost.com/. The objective was to create conversational, intelligent chatbots using Amazon Lex and AWS Lambda!

Out Slack bot - [InvoiceTron](https://www.invoicetron.com), enables you raise invoices for your clients directly via Slack. You can either download the invoice as a PDF or email the invoice to your clients via Slack. By connecting to your Stripe account, you can receive payments for the invoices directly in your Stripe account. The invoices come with a paynow button.

## Inspiration
Creating Invoices, choosing a perfect template, sending them to the customers and giving them the payment details is a very long and time consuming task. In order to make this task easier and simpler, the idea of InvoiceTron grew which saves people’s time from all this tasks and creating invoice is now just a one click process without being worried about the payment. Slack is the most popular platform among professionals and a smart bot for slack in order to invoice your customer is an application you need for your company. This bot not only solves the tiring problem of invoicing but also helps to organise your invoices.

## What it does
InvoiceTron helps you invoice your customer and keeps track of all your paid, unpaid, sent and unsent invoices. You can view and edit your past invoices anytime. Just type create invoice and after entering amount and description, you are good to send your invoice to your customer. InvoiceTron helps you connect your stripe connect after which all the payments done of your invoices created, will be accounted in your connected stripe account. Creating and viewing your customers and invoices, generating pdf of invoices on one click and integrating payments with stripe are the salient features of InvoiceTron.

## How we built it
InvoiceTron is powered by Amazon Lex, Lambda and a healthy dose of good 'ol Python Django. Slack RTM API was used in order to connect and interact with the Slack. Messages received from Slack, go to Amazon Lex and Lambda for validations and fulfilment. Once the response from Lex is received, reply is sent to Slack user using the web api of Slack. An EC2 instance is used for deploying to the server where Nginx handles all HTTP requests. We have used SQLite3 as a light weight database.

## Challenges we ran into
Getting Lex and Lambda to interact with Django was something that took a lot of research. We are also super impressed with what all Lex can do but it did come at a cost as there was a pretty steep learning curve.

## Accomplishments that we're proud of
We initially scoped InvoiceTron as a simple natural language way to generate pdf receipts so the user can send those to their clients. An intern in our team then suggested we take it one step further and allow users to integrate InvoiceTron with Stripe so as to allow them to collect payments as well. We are now confident that InvoiceTron is one of the most simplest ways to invoice and receive payments from customers.

What's next for InvoiceTron
Lots of stuff including improvements in natural language processing, i.e. understanding free form statements to create invoices in one go, supporting more payment methods like paypal and venmo and finally launching an invoicing skill for Alexa.

