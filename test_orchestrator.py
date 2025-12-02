from src.agent.orchestrator import Orchestrator

def test_orchestrator():
    """Test the Orchestrator Agent with a small subset"""
    print("🧪 Testing Orchestrator Agent...")
    print("-" * 50)
    
    # Initialize orchestrator
    orchestrator = Orchestrator(
        enrich_threshold=50.0,  # Enrich categories with score >= 50
        max_products_per_category=5,  # Small number for testing
        enrich_with_details=True
    )
    
    # Run full analysis
    print("\n🚀 Starting full analysis...")
    results = orchestrator.run_full_analysis()
    
    if results and 'error' not in results:
        print(f"\n✅ Orchestrator completed successfully!")
        print(f"   Opportunities found: {results['stats']['opportunities_found']}")
        print(f"   Categories analyzed: {results['stats']['categories_analyzed']}")
    else:
        print("\n❌ Orchestrator encountered an error")

if __name__ == "__main__":
    test_orchestrator()