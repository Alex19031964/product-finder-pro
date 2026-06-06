from pathlib import Path
from io import BytesIO
import pandas as pd
import plotly.express as px
import streamlit as st

from product_finder_web.core.calculations import scan_products, revenue_projection
from product_finder_web.core.sample_marketplace import sample_marketplace_data
from product_finder_web.db.database import save_scan, load_recent_scans, clear_history
from product_finder_web.api_clients.keepa_client import KeepaClient
from product_finder_web.api_clients.ebay_client import EbayClient
from product_finder_web.api_clients.amazon_sp_api_client import AmazonSPAPIClient


st.set_page_config(page_title="Product Finder Pro", page_icon="📦", layout="wide")

st.markdown("""
<style>
.block-container {padding-top: 1.5rem;}
.small-note {color: #9ca3af; font-size: 0.9rem;}
</style>
""", unsafe_allow_html=True)


@st.cache_data
def load_sample_supplier_data():
    return pd.read_csv(Path("data/sample_supplier_products.csv"))


def to_excel_bytes(df: pd.DataFrame) -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Opportunities")
    return output.getvalue()


def show_api_status():
    keepa = KeepaClient()
    ebay = EbayClient()
    amazon = AmazonSPAPIClient()

    st.sidebar.subheader("API status")
    st.sidebar.write("Keepa:", "✅ configured" if keepa.is_configured() else "⚠️ not configured")
    st.sidebar.write("eBay:", "✅ configured" if ebay.is_configured() else "⚠️ not configured")
    st.sidebar.write("Amazon SP-API:", "✅ configured" if amazon.is_configured() else "⚠️ not configured")
    st.sidebar.caption("Add keys to `.env` when you have approved API access.")


st.title("📦 Product Finder Pro Web")
st.caption("Local browser dashboard for supplier-to-marketplace resale opportunity analysis.")

show_api_status()

with st.sidebar:
    st.header("Scan settings")
    other_expenses = st.number_input("Other expenses per unit (£)", min_value=0.0, value=1.50, step=0.10)
    min_roi = st.slider("Minimum ROI %", 0, 200, 20)
    min_sales = st.slider("Minimum monthly sales", 0, 3000, 100)
    opportunity_filter = st.selectbox("Opportunity filter", ["All", "High", "Medium", "Low"])
    growth_rate = st.slider("Forecast monthly growth %", -20, 50, 12) / 100
    st.caption("Real turnover requires approved APIs or third-party data providers like Keepa.")

tab_dashboard, tab_import, tab_history, tab_api = st.tabs([
    "Dashboard",
    "Supplier import",
    "Saved scans",
    "API setup",
])

with tab_import:
    st.subheader("Supplier data")

    uploaded_supplier = st.file_uploader(
        "Upload supplier CSV",
        type=["csv"],
        help="Use product_name, category, supplier, cost, shipping_cost, moq, lead_time_days",
    )

    if uploaded_supplier:
        supplier_df = pd.read_csv(uploaded_supplier)
    else:
        supplier_df = load_sample_supplier_data()

    st.dataframe(supplier_df, use_container_width=True)

    st.download_button(
        "Download sample supplier CSV",
        data=Path("data/sample_supplier_products.csv").read_bytes(),
        file_name="sample_supplier_products.csv",
        mime="text/csv",
    )

    st.subheader("Marketplace signal data")

    uploaded_market = st.file_uploader(
        "Optional: upload marketplace signal CSV",
        type=["csv"],
        help="Use product_name, marketplace, selling_price, estimated_monthly_sales, competition_score",
    )

    if uploaded_market:
        marketplace_df = pd.read_csv(uploaded_market)
    else:
        marketplace_df = sample_marketplace_data()

    st.dataframe(marketplace_df, use_container_width=True)

with tab_dashboard:
    supplier_df = supplier_df if "supplier_df" in locals() else load_sample_supplier_data()
    marketplace_df = marketplace_df if "marketplace_df" in locals() else sample_marketplace_data()

    try:
        results = scan_products(supplier_df, marketplace_df, other_expenses=other_expenses)
    except Exception as exc:
        st.error(str(exc))
        st.stop()

    filtered = results[
        (results["ROI %"] >= min_roi) &
        (results["Monthly Sales"] >= min_sales)
    ]

    if opportunity_filter != "All":
        filtered = filtered[filtered["Opportunity"] == opportunity_filter]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Products scanned", len(results))
    c2.metric("Average ROI", f"{results['ROI %'].mean():.1f}%")
    c3.metric("High opportunities", int((results["Opportunity"] == "High").sum()))
    c4.metric("Potential monthly profit", f"£{filtered['Monthly Profit'].clip(lower=0).sum():,.0f}")

    st.subheader("Opportunity results")
    st.dataframe(
        filtered[[
            "Product", "Category", "Marketplace", "Total Cost", "Selling Price",
            "Profit Per Unit", "ROI %", "Monthly Sales", "Monthly Revenue",
            "Monthly Profit", "Competition", "Opportunity", "Opportunity Score"
        ]],
        use_container_width=True,
        hide_index=True,
    )

    left, right = st.columns([1.1, 1])

    with left:
        top_chart = filtered.head(10)
        if not top_chart.empty:
            fig = px.bar(
                top_chart.sort_values("Opportunity Score"),
                x="Opportunity Score",
                y="Product",
                orientation="h",
                title="Top product opportunity scores",
                hover_data=["ROI %", "Monthly Profit", "Competition"],
            )
            st.plotly_chart(fig, use_container_width=True)

    with right:
        if not filtered.empty:
            selected_product = st.selectbox("Select product for projection", filtered["Product"].tolist())
            selected = filtered[filtered["Product"] == selected_product].iloc[0]

            projection = revenue_projection(selected["Monthly Revenue"], growth_rate)
            fig2 = px.line(
                projection,
                x="Month",
                y="Projected Revenue",
                markers=True,
                title=f"Projected revenue: {selected_product}",
            )
            st.plotly_chart(fig2, use_container_width=True)

            st.write("### Product breakdown")
            st.write(f"**Supplier:** {selected['Supplier']}")
            st.write(f"**Marketplace:** {selected['Marketplace']}")
            st.write(f"**Total cost:** £{selected['Total Cost']:.2f}")
            st.write(f"**Selling price:** £{selected['Selling Price']:.2f}")
            st.write(f"**Profit per unit:** £{selected['Profit Per Unit']:.2f}")
            st.write(f"**ROI:** {selected['ROI %']:.2f}%")
            st.write(f"**Opportunity:** {selected['Opportunity']}")

    st.divider()

    col_a, col_b, col_c = st.columns(3)

    col_a.download_button(
        "Download CSV results",
        data=filtered.to_csv(index=False).encode("utf-8"),
        file_name="product_finder_results.csv",
        mime="text/csv",
    )

    col_b.download_button(
        "Download Excel results",
        data=to_excel_bytes(filtered),
        file_name="product_finder_results.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    if col_c.button("Save scan to local database"):
        save_scan(results)
        st.success("Scan saved to local SQLite database.")

with tab_history:
    st.subheader("Saved scan history")
    recent = load_recent_scans(500)
    if recent.empty:
        st.info("No saved scans yet.")
    else:
        st.dataframe(recent, use_container_width=True)
        st.download_button(
            "Download saved history CSV",
            data=recent.to_csv(index=False).encode("utf-8"),
            file_name="saved_scan_history.csv",
            mime="text/csv",
        )
        if st.button("Clear saved history"):
            clear_history()
            st.success("History cleared. Refresh the page to update.")

with tab_api:
    st.subheader("API setup")
    st.write("""
This app avoids direct website scraping. For real sales estimates and marketplace data, use approved APIs or third-party providers.

Recommended path:
1. Use supplier CSV exports from Alibaba or your supplier.
2. Use Keepa for Amazon rank/history/sales signals.
3. Use Amazon SP-API for official catalog and fee data if you are approved.
4. Use eBay Browse API for eBay listing data.
""")

    st.code("""
# .env example

KEEPA_API_KEY=your_keepa_key

AMAZON_CLIENT_ID=your_amazon_client_id
AMAZON_CLIENT_SECRET=your_amazon_client_secret
AMAZON_REFRESH_TOKEN=your_amazon_refresh_token
AMAZON_REGION=UK

EBAY_ACCESS_TOKEN=your_ebay_token
EBAY_MARKETPLACE_ID=EBAY_GB
""", language="bash")

    st.warning("The sample dashboard uses example marketplace numbers. Real turnover accuracy depends on your data provider.")
