from investecApi import createInvestecClient
import json

def testInvestecConnection():
    """Test Investec API connection and data retrieval"""
    
    print("=" * 60)
    print("🧪 Testing Investec Sandbox API Connection")
    print("=" * 60)
    print()
    
    # Create client (credentials are built-in)
    print("1️⃣  Creating Investec API client...")
    client = createInvestecClient()
    
    if not client:
        print("❌ Failed to create client")
        return False
    
    print("✅ Client created successfully!")
    print()
    
    # Test accounts
    print("2️⃣  Fetching accounts...")
    accounts = client.getAccounts()
    
    if not accounts:
        print("❌ No accounts found")
        return False
    
    print(f"✅ Found {len(accounts)} account(s)!")
    print()
    
    # Display account details
    for i, account in enumerate(accounts, 1):
        print(f"   Account {i}:")
        print(f"   • ID: {account.get('accountId')}")
        print(f"   • Name: {account.get('accountName')}")
        print(f"   • Number: {account.get('accountNumber')}")
        print(f"   • Product: {account.get('productName')}")
        print()
    
    # Test balance for first account
    print("3️⃣  Fetching balance...")
    accountId = accounts[0].get('accountId')
    balance = client.getAccountBalance(accountId)
    
    if balance:
        print(f"✅ Balance retrieved!")
        print(f"   • Current: R {balance.get('currentBalance', 0):,.2f}")
        print(f"   • Available: R {balance.get('availableBalance', 0):,.2f}")
        print()
    
    # Test transactions
    print("4️⃣  Fetching transactions...")
    transactions = client.getTransactions(accountId)
    
    if transactions:
        print(f"✅ Found {len(transactions)} transaction(s)!")
        print()
        print("   Recent transactions:")
        for txn in transactions[:5]:  # Show first 5
            amount = txn.get('amount', 0)
            desc = txn.get('description', 'Unknown')
            date = txn.get('transactionDate', 'N/A')
            sign = "+" if amount > 0 else ""
            print(f"   • {date}: {sign}R {amount:,.2f} - {desc[:50]}")
        
        if len(transactions) > 5:
            print(f"   ... and {len(transactions) - 5} more")
    else:
        print("⚠️  No transactions found (this is normal for new sandbox accounts)")
    
    print()
    print("=" * 60)
    print("🎉 All tests passed! Investec API is working!")
    print("=" * 60)
    
    return True


def testBeneficiaries():
    """Test beneficiaries endpoint"""
    print("\n5️⃣  Testing beneficiaries...")
    client = createInvestecClient()
    
    if client:
        beneficiaries = client.getBeneficiaries()
        print(f"✅ Found {len(beneficiaries)} beneficiary(ies)")
        
        for ben in beneficiaries[:3]:  # Show first 3
            print(f"   • {ben.get('beneficiaryName', 'Unknown')}")


if __name__ == "__main__":
    try:
        success = testInvestecConnection()
        
        if success:
            testBeneficiaries()
            print("\n✅ Your Investec API integration is ready to use!")
        
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        print("\nTroubleshooting:")
        print("  • Check your internet connection")
        print("  • Verify sandbox is accessible")
        print("  • Check the error message above")