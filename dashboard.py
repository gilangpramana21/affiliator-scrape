#!/usr/bin/env python3
"""
Simple Dashboard for Tokopedia Affiliator Data
"""
import json
from pathlib import Path
import pandas as pd
from datetime import datetime


def load_data():
    """Load data from JSON file"""
    json_path = Path("output/affiliators_full.json")
    
    if not json_path.exists():
        print("❌ Data file not found: output/affiliators_full.json")
        print("   Please run scraper first: python scrape_full_data.py")
        return None
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return pd.DataFrame(data)


def parse_number(value):
    """Parse Indonesian number format (268,1 rb, 1 jt, etc)"""
    if not value or pd.isna(value):
        return 0
    
    value = str(value).lower().replace(',', '.')
    
    # Extract number and unit
    import re
    match = re.search(r'([\d\.]+)\s*(rb|jt|k|m)?', value)
    
    if not match:
        return 0
    
    number = float(match.group(1))
    unit = match.group(2) if match.group(2) else ''
    
    # Convert to actual number
    if unit in ['rb', 'k']:
        return number * 1000
    elif unit in ['jt', 'm']:
        return number * 1000000
    else:
        return number


def print_dashboard(df):
    """Print dashboard to console"""
    print("\n" + "="*80)
    print("📊 TOKOPEDIA AFFILIATOR DASHBOARD")
    print("="*80)
    
    # Basic stats
    total_creators = len(df)
    with_email = df['email'].notna().sum()
    with_whatsapp = df['whatsapp'].notna().sum()
    with_contact = ((df['email'].notna()) | (df['whatsapp'].notna())).sum()
    
    print(f"\n📈 OVERVIEW")
    print(f"{'─'*80}")
    print(f"Total Creators:        {total_creators}")
    print(f"With Email:            {with_email} ({with_email/total_creators*100:.1f}%)")
    print(f"With WhatsApp:         {with_whatsapp} ({with_whatsapp/total_creators*100:.1f}%)")
    print(f"With Any Contact:      {with_contact} ({with_contact/total_creators*100:.1f}%)")
    
    # Level distribution
    if 'level' in df.columns and df['level'].notna().any():
        print(f"\n📊 LEVEL DISTRIBUTION")
        print(f"{'─'*80}")
        level_counts = df['level'].value_counts().sort_index()
        for level, count in level_counts.items():
            print(f"Level {level}:  {count} creators ({count/total_creators*100:.1f}%)")
    
    # Category distribution
    if 'category' in df.columns and df['category'].notna().any():
        print(f"\n🏷️  TOP CATEGORIES")
        print(f"{'─'*80}")
        # Get first category (before comma)
        df['main_category'] = df['category'].str.split(',').str[0]
        top_categories = df['main_category'].value_counts().head(10)
        for category, count in top_categories.items():
            print(f"{category[:40]:40} {count:3} creators ({count/total_creators*100:.1f}%)")
    
    # Followers analysis
    if 'followers' in df.columns and df['followers'].notna().any():
        print(f"\n👥 FOLLOWERS ANALYSIS")
        print(f"{'─'*80}")
        df['followers_num'] = df['followers'].apply(parse_number)
        
        avg_followers = df['followers_num'].mean()
        median_followers = df['followers_num'].median()
        max_followers = df['followers_num'].max()
        
        print(f"Average Followers:     {avg_followers:,.0f}")
        print(f"Median Followers:      {median_followers:,.0f}")
        print(f"Max Followers:         {max_followers:,.0f}")
        
        # Top creators by followers
        print(f"\n🌟 TOP 10 CREATORS BY FOLLOWERS")
        print(f"{'─'*80}")
        top_creators = df.nlargest(10, 'followers_num')[['username', 'followers', 'email', 'whatsapp']]
        for idx, row in top_creators.iterrows():
            username = row['username'] if pd.notna(row['username']) else 'N/A'
            followers = row['followers'] if pd.notna(row['followers']) else 'N/A'
            has_contact = '✅' if (pd.notna(row['email']) or pd.notna(row['whatsapp'])) else '❌'
            print(f"{username[:30]:30} {followers:15} {has_contact}")
    
    # Contact info summary
    print(f"\n📧 CREATORS WITH CONTACT INFO")
    print(f"{'─'*80}")
    creators_with_contact = df[(df['email'].notna()) | (df['whatsapp'].notna())]
    
    if len(creators_with_contact) > 0:
        for idx, row in creators_with_contact.iterrows():
            username = row.get('username', row.get('display_name', f"Creator #{row.get('index', idx)}"))
            if pd.isna(username):
                username = f"Creator #{row.get('index', idx)}"
            
            email = row['email'] if pd.notna(row['email']) else '-'
            whatsapp = row['whatsapp'] if pd.notna(row['whatsapp']) else '-'
            followers = row.get('followers', 'N/A')
            if pd.isna(followers):
                followers = 'N/A'
            
            print(f"\n{username}")
            print(f"  Followers: {followers}")
            print(f"  Email:     {email}")
            print(f"  WhatsApp:  {whatsapp}")
    else:
        print("No creators with contact info found.")
    
    # Gender distribution
    if 'gender_male' in df.columns and df['gender_male'].notna().any():
        print(f"\n👤 GENDER DISTRIBUTION (Average)")
        print(f"{'─'*80}")
        
        # Parse percentages
        df['male_pct'] = df['gender_male'].str.replace('%', '').astype(float, errors='ignore')
        df['female_pct'] = df['gender_female'].str.replace('%', '').astype(float, errors='ignore')
        
        avg_male = df['male_pct'].mean()
        avg_female = df['female_pct'].mean()
        
        print(f"Male:    {avg_male:.1f}%")
        print(f"Female:  {avg_female:.1f}%")
    
    # Age group distribution
    if 'age_group' in df.columns and df['age_group'].notna().any():
        print(f"\n🎂 AGE GROUP DISTRIBUTION")
        print(f"{'─'*80}")
        age_counts = df['age_group'].value_counts()
        for age, count in age_counts.items():
            print(f"{age}:  {count} creators ({count/total_creators*100:.1f}%)")
    
    print(f"\n{'='*80}")
    print(f"📁 Data saved to: output/affiliators_full.xlsx")
    print(f"{'='*80}\n")


def export_contact_list(df):
    """Export list of creators with contact info"""
    creators_with_contact = df[(df['email'].notna()) | (df['whatsapp'].notna())]
    
    if len(creators_with_contact) == 0:
        return
    
    # Select relevant columns
    contact_columns = ['username', 'display_name', 'followers', 'category', 'email', 'whatsapp']
    existing_columns = [col for col in contact_columns if col in creators_with_contact.columns]
    
    contact_list = creators_with_contact[existing_columns]
    
    # Save to separate Excel file
    output_path = Path("output/affiliators_with_contacts.xlsx")
    contact_list.to_excel(output_path, index=False, engine='openpyxl')
    
    print(f"📧 Exported {len(contact_list)} creators with contacts to: {output_path}")


def main():
    """Main function"""
    print("\n🚀 Loading data...")
    
    df = load_data()
    
    if df is None:
        return
    
    print(f"✅ Loaded {len(df)} creators")
    
    # Print dashboard
    print_dashboard(df)
    
    # Export contact list
    try:
        export_contact_list(df)
    except Exception as e:
        print(f"⚠️  Could not export contact list: {e}")


if __name__ == "__main__":
    main()
