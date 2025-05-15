import pandas as pd
import numpy as np
import streamlit as st
from streamlit_folium import folium_static
import folium

@st.cache_data
def load_data():
    encodings = ['utf-8', 'ISO-8859-1', 'Windows-1252', 'latin1']
    for encoding in encodings:
        try:
            df = pd.read_csv('zomato.csv', encoding=encoding)
            df.drop_duplicates(inplace=True)
            columns_to_drop = ['Address', 'Locality', 'Switch to order menu', 'URL']
            df.drop(columns=[col for col in columns_to_drop if col in df.columns], inplace=True)
            df.fillna({
                'Aggregate rating': df['Aggregate rating'].mean(), 
                'Average Cost for two': df['Average Cost for two'].median()
            }, inplace=True)
            df.dropna(subset=['City', 'Cuisines'], inplace=True)

            df['Aggregate rating'] = pd.to_numeric(df['Aggregate rating'], errors='coerce')
            df['Average Cost for two'] = df['Average Cost for two'].astype(str).str.replace(r'[^\d.]', '', regex=True)
            df['Average Cost for two'] = pd.to_numeric(df['Average Cost for two'], errors='coerce')
            df['Price Range'] = df['Average Cost for two'].apply(lambda x: 'Budget' if x < 500 else 'Moderate' if x < 1500 else 'Premium')
            df['Primary Cuisine'] = df['Cuisines'].str.split(',').str[0].str.strip().str.lower()
            return df
        except:
            continue
    st.error("❌ Could not read the file.")
    return pd.DataFrame()

def recommend_restaurants(df, cuisine_pref=None, budget_pref=None, city_pref=None, rating_threshold=3.5, top_n=5):
    filtered = df.copy()
    if cuisine_pref:
        cuisine_pref = [c.lower().strip() for c in cuisine_pref]
        filtered = filtered[
            filtered['Primary Cuisine'].isin(cuisine_pref) |
            filtered['Cuisines'].str.lower().apply(lambda x: any(c in x for c in cuisine_pref))
        ]
    if budget_pref:
        filtered = filtered[filtered['Price Range'] == budget_pref]
    if city_pref:
        filtered = filtered[filtered['City'].str.lower().str.contains(city_pref.lower())]
    filtered = filtered[filtered['Aggregate rating'] >= rating_threshold]
    if filtered.empty:
        return pd.DataFrame()
    if 'Votes' in filtered.columns:
        filtered['Score'] = (filtered['Aggregate rating'] * 0.7) + (filtered['Votes'] * 0.0001)
    else:
        filtered['Score'] = filtered['Aggregate rating']
    return filtered.sort_values('Score', ascending=False).head(top_n)[[
        'Restaurant Name', 'City', 'Cuisines', 'Aggregate rating',
        'Average Cost for two', 'Price Range', 'Latitude', 'Longitude'
    ]]

def main():
    st.title("🍽️ Zomato Restaurant Recommender")
    df = load_data()
    if df.empty:
        return
    st.sidebar.header("Your Preferences")
    cuisines = sorted(df['Primary Cuisine'].dropna().unique())
    selected_cuisines = st.sidebar.multiselect("Cuisine", cuisines, default=cuisines[:1])
    budget = st.sidebar.selectbox("Budget", ['Budget', 'Moderate', 'Premium'])
    city = st.sidebar.selectbox("City", sorted(df['City'].dropna().unique()))
    rating = st.sidebar.slider("Minimum Rating", 0.0, 5.0, 3.5, 0.1)
    top_n = st.sidebar.slider("Top N", 1, 10, 5)

    if st.sidebar.button("Find Restaurants"):
        results = recommend_restaurants(df, selected_cuisines, budget, city, rating, top_n)
        if results.empty:
            st.warning("❌ No matches found.")
        else:
            st.success(f"🍴 Found {len(results)} match(es).")
            for _, row in results.iterrows():
                with st.expander(f"{row['Restaurant Name']} — ⭐ {row['Aggregate rating']:.1f}"):
                    st.markdown(f"**Cuisine:** {row['Cuisines']}")
                    st.markdown(f"**Price:** {row['Average Cost for two']}")
                    st.markdown(f"**City:** {row['City']}")
                    if not pd.isna(row['Latitude']) and not pd.isna(row['Longitude']):
                        m = folium.Map(location=[row['Latitude'], row['Longitude']], zoom_start=14)
                        folium.Marker([row['Latitude'], row['Longitude']], tooltip=row['Restaurant Name']).add_to(m)
                        folium_static(m)

    st.subheader("Feedback")
    feedback = st.radio("Was this helpful?", ["Yes", "No", "Somewhat"])
    if st.button("Submit Feedback"):
        with open("feedback_log.csv", "a") as f:
            f.write(f"{city},{budget},{selected_cuisines},{feedback}\n")
        st.success("✅ Feedback recorded!")

    if st.checkbox("Show Sample Data"):
        st.write(df.head())

if __name__ == "__main__":
    main()
