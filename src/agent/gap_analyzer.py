from typing import List, Dict, Optional
import json
import os
from src.models.product import Product
from src.utils.logger import get_logger

logger = get_logger(__name__)

class GapAnalyzer:
    """
    Gap Analyzer Agent - The decision-making brain of the system.
    Analyzes market gaps and identifies KDP-friendly opportunities.
    Uses strong logic tailored for Noon.com market (not Amazon).
    Filters out overly competitive niches and finds viable opportunities.
    """
    
    def __init__(
        self,
        bestseller_keywords: Optional[List[str]] = None,
        max_avg_reviews: int = 50,  # Noon.com scale (not Amazon's 1000+)
        max_avg_price: float = 200.0,
        min_products_for_demand: int = 3,
        high_competition_product_count: int = 30
    ):
        """
        Initialize Gap Analyzer with Noon.com-appropriate filtering criteria
        
        Args:
            bestseller_keywords: Keywords that indicate bestsellers
            max_avg_reviews: Maximum average reviews (Noon.com scale: 50, not 1000)
            max_avg_price: Maximum average price (AED)
            min_products_for_demand: Minimum products needed to show demand
            high_competition_product_count: Product count threshold for high competition
        """
        self.bestseller_keywords = bestseller_keywords or [
            "game of thrones", "harry potter", "lord of the rings",
            "stephen king", "j.k. rowling", "george r.r. martin",
            "tolkien", "grisham", "brown", "dan brown",
            "bestseller", "bestselling", "award winning",
            "nobel prize", "pulitzer"
        ]
        self.max_avg_reviews = max_avg_reviews
        self.max_avg_price = max_avg_price
        self.min_products_for_demand = min_products_for_demand
        self.high_competition_product_count = high_competition_product_count
    
    def analyze_category(
        self, 
        category_path: str, 
        products: List[Product]
    ) -> Dict:
        """
        Analyze a single category and calculate opportunity score.
        This is the core decision-making logic.
        """
        if not products:
            return {
                'category': category_path,
                'opportunity_score': 0,
                'status': 'no_products',
                'recommendation': 'skip',
                'reason': 'No products found on Noon.com - no demand signal'
            }
        
        # Calculate metrics
        metrics = self._calculate_metrics(products)
        
        # Check for bestsellers (automatic skip - too competitive)
        if self._has_bestsellers(products):
            return {
                'category': category_path,
                'opportunity_score': 0,
                'status': 'too_competitive_bestsellers',
                'recommendation': 'skip',
                'reason': 'Contains bestsellers - too competitive for KDP publisher',
                'metrics': metrics
            }
        
        # Check competition level (using Noon.com-appropriate thresholds)
        competition_level = self._assess_competition(metrics, len(products))
        
        # Check market demand
        demand_level = self._assess_demand(metrics, len(products))
        
        # Check KDP viability
        viability = self._assess_kdp_viability(metrics)
        
        # Calculate opportunity score
        opportunity_score = self._calculate_opportunity_score(
            demand_level, competition_level, viability
        )
        
        # Make recommendation
        recommendation = self._make_recommendation(
            opportunity_score, competition_level, demand_level, metrics
        )
        
        return {
            'category': category_path,
            'opportunity_score': opportunity_score,
            'status': recommendation['status'],
            'recommendation': recommendation['action'],
            'reason': recommendation['reason'],
            'metrics': metrics,
            'demand_level': demand_level,
            'competition_level': competition_level,
            'kdp_viability': round(viability * 100, 2),
            'product_count': len(products)
        }
    
    def _calculate_metrics(self, products: List[Product]) -> Dict:
        """Calculate key metrics from products"""
        total_products = len(products)
        
        # Review metrics (handle null values)
        review_counts = [p.review_count for p in products if p.review_count is not None]
        avg_reviews = sum(review_counts) / len(review_counts) if review_counts else 0
        max_reviews = max(review_counts) if review_counts else 0
        products_with_reviews = len(review_counts)
        review_coverage = products_with_reviews / total_products if total_products > 0 else 0
        
        # Rating metrics
        ratings = [p.average_rating for p in products if p.average_rating is not None]
        avg_rating = sum(ratings) / len(ratings) if ratings else 0
        max_rating = max(ratings) if ratings else 0
        
        # Price metrics
        prices = [p.price for p in products if p.price]
        avg_price = sum(prices) / len(prices) if prices else 0
        min_price = min(prices) if prices else 0
        max_price = max(prices) if prices else 0
        price_range = max_price - min_price if prices else 0
        
        # Discount metrics (high discounts might indicate slow sales or competition)
        discounts = [p.discount_percentage for p in products if p.discount_percentage is not None]
        avg_discount = sum(discounts) / len(discounts) if discounts else 0
        max_discount = max(discounts) if discounts else 0
        high_discount_count = len([d for d in discounts if d > 50])
        discount_rate = high_discount_count / total_products if total_products > 0 else 0
        
        # Author diversity (more authors = less dominated by few authors)
        authors = [p.author for p in products if p.author]
        unique_authors = len(set(authors)) if authors else 0
        author_diversity = unique_authors / total_products if total_products > 0 else 0
        
        # Availability (low stock might indicate demand)
        availability_counts = {
            'in_stock': len([p for p in products if p.availability == "In Stock"]),
            'low_stock': len([p for p in products if p.availability == "Low Stock"]),
            'out_of_stock': len([p for p in products if p.availability == "Out of Stock"])
        }
        
        return {
            'total_products': total_products,
            'avg_reviews': round(avg_reviews, 2),
            'max_reviews': max_reviews,
            'products_with_reviews': products_with_reviews,
            'review_coverage': round(review_coverage, 2),
            'avg_rating': round(avg_rating, 2),
            'max_rating': round(max_rating, 2),
            'avg_price': round(avg_price, 2),
            'min_price': round(min_price, 2),
            'max_price': round(max_price, 2),
            'price_range': round(price_range, 2),
            'avg_discount': round(avg_discount, 2),
            'max_discount': round(max_discount, 2),
            'high_discount_rate': round(discount_rate, 2),
            'unique_authors': unique_authors,
            'author_diversity': round(author_diversity, 2),
            'availability': availability_counts
        }
    
    def _has_bestsellers(self, products: List[Product]) -> bool:
        """Check if category contains bestsellers (too competitive for KDP)"""
        for product in products:
            title_lower = product.title.lower()
            author_lower = (product.author or "").lower()
            
            # Check title for bestseller keywords
            if any(keyword in title_lower for keyword in self.bestseller_keywords):
                return True
            
            # Check author name for famous authors
            if any(keyword in author_lower for keyword in self.bestseller_keywords):
                return True
        
        return False
    
    def _assess_competition(self, metrics: Dict, product_count: int) -> str:
        """
        Assess competition level: low, medium, high
        Adjusted for Noon.com market (not Amazon scale)
        """
        avg_reviews = metrics['avg_reviews']
        max_reviews = metrics['max_reviews']
        avg_rating = metrics['avg_rating']
        avg_price = metrics['avg_price']
        avg_discount = metrics['avg_discount']
        high_discount_rate = metrics['high_discount_rate']
        
        # High competition indicators (Noon.com scale)
        # Many products = competitive market
        if product_count > self.high_competition_product_count:
            return 'high'
        
        # High average reviews (Noon.com: >50 is high, not 1000+)
        if avg_reviews > self.max_avg_reviews:
            return 'high'
        
        # Very high individual reviews
        if max_reviews > 200:  # Noon.com scale
            return 'high'
        
        # High rating + decent reviews = established competition
        if avg_rating > 4.5 and avg_reviews > 20:
            return 'high'
        
        # Very high discount rate (>50% of products heavily discounted)
        # Might indicate oversaturated market trying to compete
        if high_discount_rate > 0.5:
            return 'high'
        
        # Very low prices (<10 AED) might indicate price war/competition
        if avg_price < 10 and product_count > 10:
            return 'high'
        
        # Low competition indicators
        # Very few or no reviews = new/untapped market
        if avg_reviews < 5 and max_reviews < 20:
            return 'low'
        
        # Few products = less competition
        if product_count < 5:
            return 'low'
        
        # Moderate prices, moderate reviews = medium competition
        return 'medium'
    
    def _assess_demand(self, metrics: Dict, product_count: int) -> str:
        """
        Assess market demand: low, medium, high
        Based on product availability and variety
        """
        # High demand indicators
        if product_count >= 20:
            return 'high'
        
        # Check availability (low stock might indicate demand)
        availability = metrics['availability']
        low_stock_ratio = availability['low_stock'] / product_count if product_count > 0 else 0
        
        if product_count >= self.min_products_for_demand:
            # If many products are low stock, that's a demand signal
            if low_stock_ratio > 0.3:
                return 'high'
            return 'medium'
        
        # Low demand
        if product_count < self.min_products_for_demand:
            return 'low'
        
        return 'medium'
    
    def _assess_kdp_viability(self, metrics: Dict) -> float:
        """
        Calculate KDP viability score (0-1)
        Higher score = more suitable for KDP publisher
        """
        score = 1.0
        
        # Penalize very high prices (premium market harder to enter)
        avg_price = metrics['avg_price']
        if avg_price > self.max_avg_price:
            score -= 0.4  # Too premium
        elif avg_price > 150:
            score -= 0.2  # Premium market
        elif avg_price > 100:
            score -= 0.1
        
        # Reward moderate pricing (accessible market for KDP)
        if 15 <= avg_price <= 80:
            score += 0.15  # Sweet spot for KDP
        
        # Reward author diversity (less dominated by few authors)
        author_diversity = metrics['author_diversity']
        score += author_diversity * 0.2
        
        # Penalize very high discount rates (might indicate slow sales/oversaturation)
        if metrics['high_discount_rate'] > 0.6:
            score -= 0.2
        elif metrics['high_discount_rate'] > 0.4:
            score -= 0.1
        
        # Reward moderate discount rates (healthy market)
        if 0.1 <= metrics['high_discount_rate'] <= 0.3:
            score += 0.1
        
        # Reward low review coverage (newer market, less established)
        if metrics['review_coverage'] < 0.3:
            score += 0.1  # Less established = more opportunity
        
        # Penalize very low prices (might be price war, hard to compete)
        if avg_price < 5:
            score -= 0.15
        
        return max(0, min(1, score))  # Clamp between 0 and 1
    
    def _calculate_opportunity_score(
        self, 
        demand: str, 
        competition: str, 
        viability: float
    ) -> float:
        """
        Calculate overall opportunity score (0-100)
        Higher score = better opportunity for KDP publisher
        """
        # Convert demand to number
        demand_scores = {'low': 0.2, 'medium': 0.6, 'high': 1.0}
        demand_score = demand_scores.get(demand, 0.5)
        
        # Convert competition to number (inverse - lower competition = higher score)
        competition_scores = {'low': 1.0, 'medium': 0.6, 'high': 0.2}
        competition_score = competition_scores.get(competition, 0.5)
        
        # Weighted calculation
        opportunity = (
            demand_score * 0.35 +      # 35% weight on demand
            competition_score * 0.45 +  # 45% weight on low competition (most important!)
            viability * 0.20           # 20% weight on KDP viability
        )
        
        return round(opportunity * 100, 2)  # Convert to 0-100 scale
    
    def _make_recommendation(
        self, 
        score: float, 
        competition: str, 
        demand: str,
        metrics: Dict
    ) -> Dict:
        """Make final recommendation based on comprehensive analysis"""
        if score >= 70:
            return {
                'action': 'high_opportunity',
                'status': 'excellent',
                'reason': f'Excellent opportunity! {demand} demand, {competition} competition, KDP-friendly market'
            }
        elif score >= 50:
            return {
                'action': 'moderate_opportunity',
                'status': 'good',
                'reason': f'Good opportunity - {demand} demand, {competition} competition. Worth exploring.'
            }
        elif score >= 30:
            return {
                'action': 'low_opportunity',
                'status': 'fair',
                'reason': f'Fair opportunity - {demand} demand, {competition} competition. Consider carefully.'
            }
        else:
            return {
                'action': 'skip',
                'status': 'poor',
                'reason': f'Not viable - {demand} demand, {competition} competition. Too competitive or no demand.'
            }
    
    def analyze_all_categories(
        self, 
        scraped_results: Dict[str, List[Product]]
    ) -> List[Dict]:
        """
        Analyze all categories and return ranked opportunities.
        This is the main method that processes all scraped data.
        """
        logger.info(f"🔍 Analyzing {len(scraped_results)} categories...")
        logger.info(f"   Using Noon.com-appropriate thresholds (max reviews: {self.max_avg_reviews})")
        
        analyses = []
        
        for category_path, products in scraped_results.items():
            analysis = self.analyze_category(category_path, products)
            analyses.append(analysis)
        
        # Sort by opportunity score (highest first)
        analyses.sort(key=lambda x: x['opportunity_score'], reverse=True)
        
        # Separate opportunities from skipped categories
        opportunities = [a for a in analyses if a['recommendation'] != 'skip']
        skipped = [a for a in analyses if a['recommendation'] == 'skip']
        
        # Log summary
        high_opp = len([o for o in opportunities if o['opportunity_score'] >= 70])
        moderate_opp = len([o for o in opportunities if 50 <= o['opportunity_score'] < 70])
        low_opp = len([o for o in opportunities if o['opportunity_score'] < 50])
        
        logger.info(f"✅ Analysis complete!")
        logger.info(f"   Total categories analyzed: {len(analyses)}")
        logger.info(f"   High opportunities (70+): {high_opp}")
        logger.info(f"   Moderate opportunities (50-69): {moderate_opp}")
        logger.info(f"   Low opportunities (30-49): {low_opp}")
        logger.info(f"   Categories skipped: {len(skipped)}")
        
        return opportunities
    
    def generate_report(
        self, 
        opportunities: List[Dict],
        output_path: str = "data/gap_analysis_report.json"
    ):
        """Generate and save comprehensive analysis report"""
        high_opp = [o for o in opportunities if o['opportunity_score'] >= 70]
        moderate_opp = [o for o in opportunities if 50 <= o['opportunity_score'] < 70]
        low_opp = [o for o in opportunities if o['opportunity_score'] < 50]
        
        report = {
            'summary': {
                'total_opportunities': len(opportunities),
                'high_opportunities': len(high_opp),
                'moderate_opportunities': len(moderate_opp),
                'low_opportunities': len(low_opp),
                'analysis_date': str(opportunities[0]['metrics'].get('scraped_at', 'N/A')) if opportunities else 'N/A'
            },
            'top_opportunities': high_opp[:20],  # Top 20 high opportunities
            'moderate_opportunities': moderate_opp[:10],  # Top 10 moderate
            'all_opportunities': opportunities
        }
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"💾 Saved analysis report to {output_path}")
        logger.info(f"   Top opportunities: {len(report['top_opportunities'])}")
        
        return report
    
    def print_summary(self, opportunities: List[Dict]):
        """Print a human-readable summary of opportunities"""
        if not opportunities:
            print("\n⚠️  No opportunities found")
            return
        
        print("\n" + "="*70)
        print("📊 GAP ANALYSIS SUMMARY")
        print("="*70)
        
        high_opp = [o for o in opportunities if o['opportunity_score'] >= 70]
        moderate_opp = [o for o in opportunities if 50 <= o['opportunity_score'] < 70]
        
        if high_opp:
            print(f"\n🌟 HIGH OPPORTUNITIES (Score 70+): {len(high_opp)}")
            print("-" * 70)
            for i, opp in enumerate(high_opp[:10], 1):
                print(f"{i}. {opp['category']}")
                print(f"   Score: {opp['opportunity_score']}/100")
                print(f"   Products: {opp['product_count']} | Competition: {opp['competition_level']} | Demand: {opp['demand_level']}")
                print(f"   Reason: {opp['reason']}")
                print()
        
        if moderate_opp:
            print(f"\n✅ MODERATE OPPORTUNITIES (Score 50-69): {len(moderate_opp)}")
            print("-" * 70)
            for i, opp in enumerate(moderate_opp[:5], 1):
                print(f"{i}. {opp['category']}")
                print(f"   Score: {opp['opportunity_score']}/100 | Competition: {opp['competition_level']}")
                print()
        
        print("="*70)