"""
Battery Toll Calculator v25
Lisa McDermott structure: 14yr sizing, 7yr mini-perm, 40% balloon target
"""

import streamlit as st
import numpy as np
import numpy_financial as npf

st.set_page_config(page_title="Battery Toll Calculator | Modo Energy", layout="centered", initial_sidebar_state="collapsed")

# Core parameters (Lisa's structure)
CAPEX = 610          # €k/MW
OPEX = 10            # €k/MW/yr
EURIBOR = 2.25       # %
TOLL_TENOR = 7       # years
SIZING_TENOR = 14    # years (15yr warranty - 1yr buffer)
LOAN_TENOR = 7       # years (mini-perm maturity)
PROJECT_LIFE = 15    # years
TARGET_BALLOON = 40  # % ("don't want more than 40% balloon")

# Revenue data from Modo forecasts (€k/MW/year) - COD 2027
REVENUE_DATA = {
'p99': [131, 65, 43, 37, 34, 32, 32, 32, 32, 31, 32, 34, 35, 36, 38],
'p50': [208, 101, 67, 58, 54, 51, 51, 50, 50, 50, 50, 53, 52, 51, 51],
'p1':  [284, 138, 91, 79, 74, 70, 70, 67, 68, 69, 69, 72, 69, 66, 65],
}

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap');
    html, body, [class*="css"], .stMarkdown, p, div, span, label {
        font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }
    #MainMenu, footer, header, .stDeployButton, div[data-testid="stToolbar"] {visibility: hidden; display: none;}
    .block-container {padding: 1rem 1.5rem !important; max-width: 900px !important;}
    
    .disclaimer {font-size: 11px; color: #64748b; text-align: center; padding: 8px 12px; background: #f8fafc; border-radius: 6px; margin-bottom: 12px; border: 1px solid #e2e8f0;}
    
    .header-row {display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; padding-bottom: 12px; border-bottom: 2px solid #e2e8f0;}
    .main-title {font-size: 22px; font-weight: 700; color: #1a1a2e;}
    .brand-text {font-size: 13px; color: #1a1a2e; font-weight: 600;}
    
    .input-label {font-size: 13px; color: #475569; margin-bottom: 6px;}
    
    .capital-row {font-size: 12px; color: #64748b; margin: 4px 0 8px 0;}
    
    .terms-row {display: flex; flex-wrap: wrap; gap: 8px; padding-top: 10px; border-top: 1px solid #f1f5f9; margin-top: 8px;}
    .term-chip {font-size: 11px; color: #475569; background: #f8fafc; padding: 4px 8px; border-radius: 4px;}
    .term-chip strong {color: #1e293b;}
    
    .result-card {border-radius: 10px; padding: 14px 16px; color: white; margin-bottom: 8px;}
    .result-card.pass {background: linear-gradient(135deg, #10b981 0%, #059669 100%);}
    .result-card.warn {background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);}
    .result-card.fail {background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);}
    .result-header {display: flex; justify-content: space-between; align-items: flex-start;}
    .result-label {font-size: 10px; opacity: 0.9; text-transform: uppercase; letter-spacing: 0.03em; margin-bottom: 4px;}
    .result-value {font-size: 28px; font-weight: 700; line-height: 1.1;}
    .result-detail {font-size: 12px; opacity: 0.9; margin-top: 4px;}
    .result-badge {font-size: 9px; font-weight: 600; padding: 4px 10px; border-radius: 4px; background: rgba(255,255,255,0.2);}
    .result-footer {font-size: 12px; opacity: 0.85; margin-top: 10px; padding-top: 10px; border-top: 1px solid rgba(255,255,255,0.2);}
    
    .footer {text-align: center; font-size: 10px; color: #94a3b8; margin-top: 12px; padding-top: 10px; border-top: 1px solid #f1f5f9;}
    
    div[data-testid="stNumberInput"] label {display: none !important;}
    div[data-testid="stNumberInput"] input {font-size: 14px !important; padding: 8px 12px !important; border: 1px solid #e2e8f0 !important; border-radius: 8px !important; background: #f8fafc !important;}
    div[data-testid="stNumberInput"] > div {max-width: 120px;}
    
    div[data-testid="stSlider"] {padding-top: 0 !important; padding-bottom: 0 !important;}
    div[data-testid="stSlider"] label {display: none !important;}
    
    div[data-testid="stSelectbox"] label {display: none !important;}
    div[data-testid="stSelectbox"] > div > div {font-size: 14px !important; background: #f8fafc !important; border: 1px solid #e2e8f0 !important; border-radius: 8px !important;}
    
    .method-section {border: 1px solid #e2e8f0; border-radius: 8px; margin-top: 16px; overflow: hidden;}
    .method-header {padding: 12px 16px; font-size: 13px; font-weight: 500; color: #475569; cursor: pointer; background: #fff; border: none; width: 100%; text-align: left;}
    .method-header:hover {background: #f8fafc;}
    .method-content {padding: 0 16px 16px 16px; font-size: 12px; color: #475569; line-height: 1.6; border-top: 1px solid #f1f5f9;}
    .method-content strong {color: #1e293b;}
</style>
""", unsafe_allow_html=True)

def get_dscr_target(toll_pct): 
    return 1.80 - toll_pct * 0.005

def get_margin_bps(toll_pct): 
    return 280 - toll_pct * 0.80

def calculate_project(toll_pct, toll_price, gearing):
    """
    Calculate project financials with Lisa's mini-perm structure.
    
    Structure:
    - 14yr sizing tenor (15yr warranty - 1yr buffer)
    - 7yr loan maturity (mini-perm)
    - 40% balloon at year 7, refinanced over years 8-14
    """
    dscr_target = get_dscr_target(toll_pct)
    margin_bps = get_margin_bps(toll_pct)
    all_in_rate = (EURIBOR + margin_bps / 100) / 100
    
    # Capital structure (€ per MW)
    debt = CAPEX * gearing / 100 * 1000
    equity = CAPEX * 1000 - debt
    
    toll_fraction = toll_pct / 100
    
    # Balloon mechanics
    balloon_at_7 = debt * TARGET_BALLOON / 100
    principal_paid_1_7 = debt - balloon_at_7  # 60% of debt
    principal_per_year_1_7 = principal_paid_1_7 / LOAN_TENOR
    

    
    # Years 8-14: amortize remaining 40% over 7 years
    principal_per_year_8_14 = balloon_at_7 / (SIZING_TENOR - LOAN_TENOR)
    
    def build_debt_service():
        """Build debt service schedule with sweep to 40% balloon."""
        if debt <= 0:
            return [0] * PROJECT_LIFE
        
        debt_service = []
        outstanding = debt
        
        # Years 1-7: accelerated principal (sweep) + interest
        for i in range(LOAN_TENOR):
            interest = outstanding * all_in_rate
            ds = principal_per_year_1_7 + interest
            debt_service.append(ds)
            outstanding -= principal_per_year_1_7
        
        # Years 8-14: balloon amortization + interest
        for i in range(SIZING_TENOR - LOAN_TENOR):
            interest = outstanding * all_in_rate
            ds = principal_per_year_8_14 + interest
            debt_service.append(ds)
            outstanding -= principal_per_year_8_14
        
        # Year 15: no debt
        debt_service.append(0)
        
        return debt_service
    
    def build_revenue(forecast):
        """Build annual revenue mixing toll and merchant."""
        revenue = []
        for i in range(PROJECT_LIFE):
            if i < TOLL_TENOR:
                rev = toll_price * toll_fraction + forecast[i] * (1 - toll_fraction)
            else:
                rev = forecast[i]
            revenue.append(rev * 1000)
        return revenue
    
    debt_service = build_debt_service()
    
    def calc_scenario(forecast):
        """Calculate DSCR and IRR for a given revenue scenario."""
        revenue = build_revenue(forecast)
        net_op = [revenue[i] - OPEX * 1000 for i in range(PROJECT_LIFE)]
        
        # DSCRs for sizing period
        dscrs = []
        for i in range(SIZING_TENOR):
            if debt_service[i] > 0:
                dscrs.append(net_op[i] / debt_service[i])
            else:
                dscrs.append(99)
        
        min_dscr = min(dscrs) if dscrs else 99
        min_dscr_year = dscrs.index(min_dscr) + 1 if dscrs else 0
        
        # Equity cash flows
        equity_cf = [net_op[i] - debt_service[i] for i in range(PROJECT_LIFE)]
        
        try:
            irr = npf.irr([-equity] + equity_cf) * 100
            if np.isnan(irr) or irr < -50 or irr > 200:
                irr = -99
        except:
            irr = -99
        
        return {
            'irr': irr,
            'min_dscr': min_dscr,
            'min_dscr_year': min_dscr_year,
        }
    
    low = calc_scenario(REVENUE_DATA['p99'])
    base = calc_scenario(REVENUE_DATA['p50'])
    high = calc_scenario(REVENUE_DATA['p1'])
    
    return {
        'dscr_target': dscr_target,
        'all_in_rate': all_in_rate * 100,
        'debt': debt / 1000,
        'equity': equity / 1000,
        'debt_feasible': low['min_dscr'] >= dscr_target,
        'low': low,
        'base': base,
        'high': high,
    }


# Disclaimer & Header
st.markdown('<div class="disclaimer">For educational purposes only</div>', unsafe_allow_html=True)
st.markdown('<div class="header-row"><div class="main-title">Battery Toll Calculator</div><div class="brand-text">Modo Energy</div></div>', unsafe_allow_html=True)
st.markdown('<p style="font-size: 13px; color: #64748b; margin-top: -12px; margin-bottom: 16px;">Explore how toll agreements enable higher leverage. Try setting 0% toll at 70% gearing—then increase toll % to see when it becomes feasible.</p>', unsafe_allow_html=True)

left_col, right_col = st.columns([1, 1.1], gap="large")

with left_col:
    # Toll price
    st.markdown('<div class="input-label">Toll Price (€k/MW/yr)</div>', unsafe_allow_html=True)
    toll_price = st.number_input("price", 80, 140, 120, 5, label_visibility="collapsed")
    
    # Toll coverage
    st.markdown('<div class="input-label">Revenue under toll (%)</div>', unsafe_allow_html=True)
    toll_pct = st.slider("toll", 0, 100, 80, label_visibility="collapsed")
    
    # Gearing
    st.markdown('<div class="input-label">Gearing %</div>', unsafe_allow_html=True)
    gearing = st.slider("gearing", 30, 85, 70, label_visibility="collapsed")
    
    result = calculate_project(toll_pct, toll_price, gearing)
    
    st.markdown(f'<div class="capital-row">€{result["debt"]:.0f}k debt / €{result["equity"]:.0f}k equity per MW</div>', unsafe_allow_html=True)
    
    st.markdown(f'''
    <div class="terms-row">
        <span class="term-chip"><strong>{result["dscr_target"]:.2f}×</strong> DSCR target</span>
        <span class="term-chip"><strong>{result["all_in_rate"]:.1f}%</strong> rate</span>
    </div>
    ''', unsafe_allow_html=True)

with right_col:
    hurdle = 10
    low_irr = result['low']['irr']
    base_irr = result['base']['irr']
    high_irr = result['high']['irr']
    min_dscr = result['low']['min_dscr']
    min_dscr_year = result['low']['min_dscr_year']
    dscr_target = result['dscr_target']
    
    # Debt card
    debt_class = "pass" if result['debt_feasible'] else "fail"
    debt_badge = "FEASIBLE" if result['debt_feasible'] else "NOT FEASIBLE"
    dscr_margin = min_dscr - dscr_target
    
    period_label = "toll" if min_dscr_year <= TOLL_TENOR else "merchant"
    
    st.markdown(f'''
    <div class="result-card {debt_class}">
        <div class="result-header">
            <div>
                <div class="result-label">Min DSCR (yr {min_dscr_year}, {period_label})</div>
                <div class="result-value">{min_dscr:.2f}×</div>
                <div class="result-detail">vs {dscr_target:.2f}× target ({"+" if dscr_margin >= 0 else ""}{dscr_margin:.2f}×)</div>
            </div>
            <div class="result-badge">{debt_badge}</div>
        </div>
    </div>
    ''', unsafe_allow_html=True)
    
    # Equity card
    eq_class = "pass" if low_irr >= hurdle else "warn" if base_irr >= hurdle else "fail"
    eq_badge = "MEETS HURDLE" if low_irr >= hurdle else "BASE MEETS HURDLE" if base_irr >= hurdle else "BELOW HURDLE"
    
    st.markdown(f'''
    <div class="result-card {eq_class}">
        <div class="result-header">
            <div>
                <div class="result-label">Equity IRR (15yr)</div>
                <div class="result-value">{base_irr:.1f}%</div>
                <div class="result-detail">vs {hurdle}% hurdle</div>
            </div>
            <div class="result-badge">{eq_badge}</div>
        </div>
        <div class="result-footer">Range: {low_irr:.0f}% – {high_irr:.0f}% (low – high)</div>
    </div>
    ''', unsafe_allow_html=True)

# Methodology section
st.markdown('''
<details class="method-section">
<summary class="method-header">Methodology</summary>
<div class="method-content">

<p><strong>How debt works</strong><br>
Lenders size debt based on the project's ability to service interest and principal from operating cash flow. The key metric is the debt service coverage ratio (DSCR): how many times over can the project pay its annual debt obligations?</p>

<p>Higher toll coverage means more predictable revenue, so lenders accept a lower DSCR cushion. A fully merchant project needs ~1.8× coverage; a fully tolled project might only need ~1.3×. Lower coverage requirements mean more debt for the same cash flow.</p>

<p><strong>Why toll enables leverage</strong><br>
Toll doesn't create higher returns directly—it compresses the revenue distribution. But that stability lets lenders extend more debt. Higher debt means less equity required, and the same project profit spread across less equity means higher equity returns.</p>

<p><strong>The structure</strong><br>
Debt is sized assuming a 14-year repayment period (matching typical battery warranties). The loan itself matures at year 7 with ~40% still outstanding, which gets refinanced. Revenue forecasts come from Modo's German market model—the calculator tests the low case to check if debt covenants hold, and shows returns across low, base, and high scenarios.</p>

<p><strong>What "not feasible" means</strong><br>
If the DSCR falls below target in any year, lenders won't offer that structure. You'd need to reduce gearing until it passes—which is exactly why merchant projects can't achieve the same leverage as tolled ones.</p>

<hr style="border: none; border-top: 1px solid #e2e8f0; margin: 12px 0;">
<span style="font-size: 10px; color: #94a3b8;">€625k/MW CapEx · €10k/MW OpEx · 2hr duration · 7yr toll · 15yr project life · COD 2027</span>

</div>
</details>
''', unsafe_allow_html=True)

st.markdown('<div class="footer">2hr duration · 7yr toll tenor · 15yr project life · COD 2027</div>', unsafe_allow_html=True)
