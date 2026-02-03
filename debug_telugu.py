import asyncio
import os
import sys
from dotenv import load_dotenv

# Load env vars
load_dotenv()

# Force UTF-8 for Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

from agent.telugu_writer import TeluguWriter

# Setup logging
import logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("debug_telugu")

async def test_telugu_generation():
    writer = TeluguWriter()
    
    # Example Article (similar to what user wants)
    english_headline = "Nara Lokesh announces Quantum Computer in Andhra Pradesh by July"
    english_summary = """
    Andhra Pradesh IT and Education Minister Nara Lokesh has announced that the state will take a key step forward in the field of Quantum Computing. 
    Speaking at the World Economic Forum (WEF) summit in Davos, Switzerland, he revealed that South Asia's most powerful quantum computer will be unveiled in Amaravati by July 2026.
    He participated in a discussion on "Accelerating Quantum Innovation with Skills and Collaboration".
    Lokesh stated that the quantum computing market, which was $1.3 billion in 2024, is expected to reach $20 billion by 2030 with a CAGR of 41.8%.
    He emphasized the need to bridge the skills gap, noting that only one-third of the required experts are available globally.
    """
    
    print("\n" + "="*50)
    print("🧪 TESTING TELUGU GENERATION (DEBUG MODE)")
    print("="*50)
    print(f"\n🇺🇸 ORIGINAL ENGLISH:\nHeadline: {english_headline}\nSummary: {english_summary}\n")
    
    print("-" * 50)
    print("🙏 Generating... (Please wait)")
    
    try:
        result = await writer.write(english_headline, english_summary)
        
        print("\n" + "="*50)
        print("🇮🇳 GENERATED TELUGU OUTPUT:")
        print("="*50)
        print(f"\n📢 HEADLINE ({len(result['headline'])} chars):\n{result['headline']}\n")
        print(f"📝 SUMMARY ({len(result['summary'])} chars):\n{result['summary']}\n")
        
        # Check for loan words (simple check)
        loan_words = ["క్వాంటమ్", "కంప్యూటర్", "డేటా", "టెక్నాలజీ", "మార్కెట్", "డాలర్", "స్కిల్"]
        found_loans = [w for w in loan_words if w in result['summary'] or w in result['headline']]
        
        print("-" * 50)
        print(f"🔍 LOAN WORD CHECK: Found {len(found_loans)} target loan words: {found_loans}")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_telugu_generation())
