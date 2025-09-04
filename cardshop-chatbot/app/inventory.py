import pandas as pd
from typing import List, Optional, Dict, Any
from rapidfuzz import fuzz
import logging
from pathlib import Path

from .models import Card, SearchFilter, CardCondition, CardRarity

logger = logging.getLogger(__name__)


class InventoryManager:
    def __init__(self, csv_path: str):
        self.csv_path = Path(csv_path)
        self._df: Optional[pd.DataFrame] = None
        self._load_inventory()
    
    def _load_inventory(self) -> None:
        """Load inventory from CSV file"""
        try:
            if self.csv_path.exists():
                self._df = pd.read_csv(self.csv_path)
                logger.info(f"Loaded {len(self._df)} cards from inventory")
            else:
                logger.error(f"Inventory file not found: {self.csv_path}")
                self._df = pd.DataFrame()
        except Exception as e:
            logger.error(f"Error loading inventory: {e}")
            self._df = pd.DataFrame()
    
    def reload_inventory(self) -> bool:
        """Reload inventory from CSV file"""
        try:
            self._load_inventory()
            return True
        except Exception as e:
            logger.error(f"Error reloading inventory: {e}")
            return False
    
    def search_cards(self, query: str, max_results: int = 10, fuzzy_threshold: int = 70) -> List[Card]:
        """Search for cards by name with fuzzy matching"""
        if self._df is None or self._df.empty:
            return []
        
        if not query.strip():
            return []
        
        query_lower = query.lower().strip()
        
        # Exact matches first
        exact_matches = self._df[self._df['name'].str.lower().str.contains(query_lower, na=False, regex=False)]
        
        # Fuzzy matches for remaining results
        fuzzy_matches = []
        if len(exact_matches) < max_results:
            remaining_df = self._df[~self._df.index.isin(exact_matches.index)]
            
            for _, row in remaining_df.iterrows():
                card_name = str(row['name']).lower()
                similarity = fuzz.partial_ratio(query_lower, card_name)
                
                if similarity >= fuzzy_threshold:
                    fuzzy_matches.append((similarity, row))
            
            # Sort by similarity score and take top results
            fuzzy_matches.sort(key=lambda x: x[0], reverse=True)
            fuzzy_matches = [match[1] for match in fuzzy_matches[:max_results - len(exact_matches)]]
        
        # Combine results
        all_matches = pd.concat([exact_matches, pd.DataFrame(fuzzy_matches)], ignore_index=True) if fuzzy_matches else exact_matches
        
        return self._df_to_cards(all_matches.head(max_results))
    
    def check_stock(self, card_name: str) -> Dict[str, Any]:
        """Check stock for a specific card name"""
        if self._df is None or self._df.empty:
            return {"found": False, "message": "Inventory not available"}
        
        card_name_lower = card_name.lower().strip()
        matches = self._df[self._df['name'].str.lower().str.contains(card_name_lower, na=False, regex=False)]
        
        if matches.empty:
            # Try fuzzy matching
            fuzzy_results = self.search_cards(card_name, max_results=3, fuzzy_threshold=80)
            if fuzzy_results:
                similar_names = [card.name for card in fuzzy_results]
                return {
                    "found": False,
                    "message": f"Card '{card_name}' not found. Did you mean: {', '.join(similar_names)}?",
                    "suggestions": fuzzy_results
                }
            return {"found": False, "message": f"Card '{card_name}' not found in inventory"}
        
        in_stock = matches[matches['quantity'] > 0]
        total_quantity = matches['quantity'].sum()
        in_stock_quantity = in_stock['quantity'].sum()
        
        return {
            "found": True,
            "total_variants": len(matches),
            "in_stock_variants": len(in_stock),
            "total_quantity": int(total_quantity),
            "in_stock_quantity": int(in_stock_quantity),
            "cards": self._df_to_cards(matches),
            "message": f"Found {len(matches)} variant(s) of '{card_name}', {in_stock_quantity} in stock"
        }
    
    def get_card_details(self, card_id: int) -> Optional[Card]:
        """Get details for a specific card ID"""
        if self._df is None or self._df.empty:
            return None
        
        card_row = self._df[self._df['card_id'] == card_id]
        if card_row.empty:
            return None
        
        return self._row_to_card(card_row.iloc[0])
    
    def filter_by_set(self, set_name: str, max_results: int = 10) -> List[Card]:
        """Filter cards by set name"""
        if self._df is None or self._df.empty:
            return []
        
        set_matches = self._df[self._df['set_name'].str.contains(set_name, case=False, na=False)]
        return self._df_to_cards(set_matches.head(max_results))
    
    def filter_by_price_range(self, min_price: float, max_price: float, max_results: int = 10) -> List[Card]:
        """Filter cards by price range"""
        if self._df is None or self._df.empty:
            return []
        
        price_matches = self._df[(self._df['price_cad'] >= min_price) & (self._df['price_cad'] <= max_price)]
        return self._df_to_cards(price_matches.head(max_results))
    
    def advanced_search(self, filters: SearchFilter, max_results: int = 10) -> List[Card]:
        """Advanced search with multiple filters"""
        if self._df is None or self._df.empty:
            return []
        
        filtered_df = self._df.copy()
        
        # Apply name filter
        if filters.name:
            name_lower = filters.name.lower().strip()
            filtered_df = filtered_df[filtered_df['name'].str.lower().str.contains(name_lower, na=False, regex=False)]
        
        # Apply set filter
        if filters.set_name:
            filtered_df = filtered_df[filtered_df['set_name'].str.contains(filters.set_name, case=False, na=False)]
        
        # Apply price filters
        if filters.min_price is not None:
            filtered_df = filtered_df[filtered_df['price_cad'] >= filters.min_price]
        
        if filters.max_price is not None:
            filtered_df = filtered_df[filtered_df['price_cad'] <= filters.max_price]
        
        # Apply condition filter
        if filters.condition:
            filtered_df = filtered_df[filtered_df['condition'] == filters.condition.value]
        
        # Apply rarity filter
        if filters.rarity:
            filtered_df = filtered_df[filtered_df['rarity'] == filters.rarity.value]
        
        # Apply stock filter
        if filters.in_stock_only:
            filtered_df = filtered_df[filtered_df['quantity'] > 0]
        
        return self._df_to_cards(filtered_df.head(max_results))
    
    def get_price_range(self) -> Dict[str, float]:
        """Get min and max prices in inventory"""
        if self._df is None or self._df.empty:
            return {"min_price": 0.0, "max_price": 0.0}
        
        return {
            "min_price": float(self._df['price_cad'].min()),
            "max_price": float(self._df['price_cad'].max())
        }
    
    def get_available_sets(self) -> List[str]:
        """Get list of available sets"""
        if self._df is None or self._df.empty:
            return []
        
        return sorted(self._df['set_name'].dropna().unique().tolist())
    
    def get_inventory_stats(self) -> Dict[str, Any]:
        """Get inventory statistics"""
        if self._df is None or self._df.empty:
            return {
                "total_cards": 0,
                "unique_cards": 0,
                "in_stock_cards": 0,
                "total_value": 0.0,
                "sets": []
            }
        
        in_stock_df = self._df[self._df['quantity'] > 0]
        
        return {
            "total_cards": int(self._df['quantity'].sum()),
            "unique_cards": len(self._df),
            "in_stock_cards": int(in_stock_df['quantity'].sum()),
            "total_value": float((self._df['price_cad'] * self._df['quantity']).sum()),
            "sets": self.get_available_sets()
        }
    
    def _df_to_cards(self, df: pd.DataFrame) -> List[Card]:
        """Convert DataFrame rows to Card objects"""
        cards = []
        for _, row in df.iterrows():
            try:
                card = self._row_to_card(row)
                if card:
                    cards.append(card)
            except Exception as e:
                logger.warning(f"Error converting row to card: {e}")
                continue
        return cards
    
    def _row_to_card(self, row: pd.Series) -> Optional[Card]:
        """Convert a pandas Series row to Card object"""
        try:
            return Card(
                card_id=int(row['card_id']),
                name=str(row['name']),
                set_name=str(row['set_name']),
                rarity=CardRarity(row['rarity']),
                condition=CardCondition(row['condition']),
                price_cad=float(row['price_cad']),
                quantity=int(row['quantity']),
                image_url=str(row['image_url']) if pd.notna(row['image_url']) else None,
                description=str(row['description']) if pd.notna(row['description']) else None
            )
        except (ValueError, KeyError) as e:
            logger.warning(f"Error creating card from row: {e}")
            return None