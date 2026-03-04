"""
Health Facility Performance Dashboard
Interactive dashboard for analyzing HC/MHC performance vs Hospitals across Rwanda
"""

from shiny import App, ui, render, reactive
from shiny.types import ImgData
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# Import data processing functions from the notebook
import sys
sys.path.append('.')
from hmis_ingestion_aggregate import extract_dhis2_data
from hmis_cleaning_and_grouping import prepare_pfp_dataframe

# ====================================================
# DATA LOADING AND PROCESSING
# ====================================================

def load_and_process_data():
    """Load and process facility data"""
    
    # Extract data
    df_final_opd = extract_dhis2_data(
        credential_file='DHIS2_credential.json',
        data_element_file='opd_cases_anc_deliveries_data_element.xlsx',
        start_date="2024-07-01",
        end_date="2025-06-30"
    )
    
    # Filter for relevant facilities
    filtered_df = df_final_opd[df_final_opd['facility_category'].isin([
        'Health Center', 'District Hospital', 'L2TH',
        'Medicalized Health Center', 'Provincial Hospital',
        'Teaching Hospital', 'Referral Hospital'
    ])]
    
    # Aggregate data
    result = filtered_df.groupby(['dataElement', 'district','sub_district', 
                                  'sector', 'name', 'facility_category']).agg({
        'value': 'sum'
    }).reset_index()
    
    # Define data element mappings
    DATA_ELEMENT_MAP = {
        "ri0XrmXSpEC": "ANC",
        "T6H8cO1Tr5t": "OPD_new",
        "o73Sit5drOc": "OPD_old",
        "TWmX6JS19hO": "Deliveries",
        "o84exadtl82": "Labor_referrals",
        "fICuyReInRd": "Obstetric_complication_referrals"
    }
    
    # Filter and pivot data
    df_filtered = result[result["dataElement"].isin(DATA_ELEMENT_MAP.keys())]
    
    facility_summary = (
        df_filtered
        .assign(indicator=df_filtered["dataElement"].map(DATA_ELEMENT_MAP))
        .pivot_table(
            index=['district', 'sector', 'sub_district', 'name', 'facility_category'],
            columns="indicator",
            values="value",
            aggfunc="sum",
            fill_value=0
        )
        .reset_index()
    )
    
    # Add Total OPD column
    facility_summary["Total_OPD"] = facility_summary["OPD_new"] + facility_summary["OPD_old"]
    
    # Remove facilities with zero activity
    activity_columns = ["ANC", "OPD_new", "OPD_old", "Deliveries"]
    facility_summary = facility_summary[
        (facility_summary[activity_columns] > 0).any(axis=1)
    ]
    
    return facility_summary

def identify_outperformers(df, sub_district, metric):
    """Identify HC/MHC that outperform hospitals in a sub-district"""
    
    sub_df = df[df['sub_district'] == sub_district].copy()
    
    hospitals = sub_df[sub_df['facility_category'].isin([
        'District Hospital', 'Provincial Hospital', 'L2TH', 'Teaching Hospital'
    ])]
    
    outperformers = []
    if len(hospitals) > 0 and hospitals[metric].min() > 0:
        min_hospital_value = hospitals[metric].min()
        
        hc_mhc = sub_df[sub_df['facility_category'].isin([
            'Health Center', 'Medicalized Health Center'
        ])]
        
        for _, facility in hc_mhc.iterrows():
            if facility[metric] > min_hospital_value:
                outperformers.append({
                    'name': facility['name'],
                    'category': facility['facility_category'],
                    'value': facility[metric],
                    'hospital_min': min_hospital_value,
                    'difference': facility[metric] - min_hospital_value,
                    'percentage': ((facility[metric] / min_hospital_value - 1) * 100)
                })
    
    return outperformers

# ====================================================
# UI DEFINITION
# ====================================================

app_ui = ui.page_navbar(
    ui.nav_panel(
        "Facility Analysis",
        ui.layout_sidebar(
            ui.sidebar(
                ui.h4("Filters", class_="text-primary mb-3"),
                ui.input_select(
                    "sub_district",
                    "Select Sub-District:",
                    choices=["Loading..."],
                    selected=None,
                    width="100%"
                ),
                ui.input_select(
                    "metric",
                    "Select Metric:",
                    choices={
                        "ANC": "ANC (Antenatal Care)",
                        "OPD_new": "OPD New Cases",
                        "OPD_old": "OPD Old Cases", 
                        "Total_OPD": "Total OPD",
                        "Deliveries": "Deliveries",
                        "Labor_referrals": "Labor Referrals",
                        "Obstetric_complication_referrals": "Obstetric Complication Referrals"
                    },
                    selected="Total_OPD",
                    width="100%"
                ),
                ui.input_checkbox(
                    "show_outperformers_only",
                    "Show Only Outperformers",
                    value=False
                ),
                ui.hr(),
                ui.h5("Summary Statistics"),
                ui.output_ui("summary_stats"),
                width=300,
                bg="#f8f9fa"
            ),
            ui.navset_card_tab(
                ui.nav_panel(
                    "Facility Comparison",
                    ui.row(
                        ui.column(12, ui.output_plot("facility_chart", height="600px"))
                    ),
                    ui.row(
                        ui.column(12, 
                            ui.card(
                                ui.card_header("Outperformers Alert"),
                                ui.output_ui("outperformers_alert"),
                                full_screen=False
                            )
                        )
                    )
                ),
                ui.nav_panel(
                    "District Overview",
                    ui.row(
                        ui.column(12, ui.output_plot("district_heatmap", height="700px"))
                    )
                ),
                ui.nav_panel(
                    "Top Performers",
                    ui.row(
                        ui.column(6, ui.output_plot("top_outperformers", height="500px")),
                        ui.column(6, ui.output_plot("category_comparison", height="500px"))
                    ),
                    ui.row(
                        ui.column(12, ui.output_data_frame("outperformers_table"))
                    )
                ),
                ui.nav_panel(
                    "Trends Analysis",
                    ui.row(
                        ui.column(12, ui.output_plot("multi_metric_comparison", height="600px"))
                    ),
                    ui.row(
                        ui.column(6, ui.output_plot("scatter_analysis", height="400px")),
                        ui.column(6, ui.output_plot("box_plot_comparison", height="400px"))
                    )
                )
            )
        )
    ),
    ui.nav_panel(
        "About",
        ui.div(
            ui.h2("Health Facility Performance Dashboard"),
            ui.hr(),
            ui.p("This dashboard analyzes health facility performance across Rwanda, specifically identifying cases where Health Centers (HC) and Medicalized Health Centers (MHC) outperform higher-level facilities."),
            ui.h4("Key Features:"),
            ui.tags.ul(
                ui.tags.li("Interactive visualization of facility performance by sub-district"),
                ui.tags.li("Automatic identification of HC/MHC facilities outperforming hospitals"),
                ui.tags.li("Multiple metrics: ANC, OPD, Deliveries, and Referrals"),
                ui.tags.li("Color-coded visualizations for easy pattern recognition")
            ),
            ui.h4("Color Coding:"),
            ui.tags.ul(
                ui.tags.li(ui.span("🔴 Red: ", style="color: red; font-weight: bold;"), "HC/MHC outperforming hospitals"),
                ui.tags.li(ui.span("🔵 Blue: ", style="color: blue; font-weight: bold;"), "Hospitals (District, Provincial, L2TH)"),
                ui.tags.li(ui.span("🟡 Gold: ", style="color: gold; font-weight: bold;"), "Medicalized Health Centers"),
                ui.tags.li(ui.span("🟢 Green: ", style="color: lightgreen; font-weight: bold;"), "Regular Health Centers")
            ),
            class_="p-4"
        )
    ),
    title="Rwanda Health Facility Dashboard",
    inverse=True,
    bg="#2c3e50"
)

# ====================================================
# SERVER LOGIC
# ====================================================

def server(input, output, session):
    
    # Load data reactively
    @reactive.calc
    def facility_data():
        return load_and_process_data()
    
    # Update sub-district choices
    @reactive.effect
    def _():
        df = facility_data()
        choices = sorted(df['sub_district'].unique())
        ui.update_select("sub_district", choices=choices, selected=choices[0])
    
    # Filtered data based on selections
    @reactive.calc
    def filtered_data():
        df = facility_data()
        return df[df['sub_district'] == input.sub_district()]
    
    # Identify outperformers
    @reactive.calc
    def current_outperformers():
        df = facility_data()
        return identify_outperformers(df, input.sub_district(), input.metric())
    
    # Main facility comparison chart
    @output
    @render.plot
    def facility_chart():
        import plotly.graph_objects as go
        
        df = filtered_data()
        metric = input.metric()
        outperformers = current_outperformers()
        outperformer_names = [o['name'] for o in outperformers]
        
        # Sort by metric value
        df_sorted = df.sort_values(metric, ascending=False)
        
        # Filter if showing only outperformers
        if input.show_outperformers_only() and outperformer_names:
            df_sorted = df_sorted[df_sorted['name'].isin(outperformer_names)]
        
        # Set colors
        colors = []
        for _, row in df_sorted.iterrows():
            if row['name'] in outperformer_names:
                colors.append('#FF0000')  # Red for outperformers
            elif row['facility_category'] == 'Medicalized Health Center':
                colors.append('#FFD700')  # Gold
            elif row['facility_category'] in ['District Hospital', 'Provincial Hospital', 'L2TH']:
                colors.append('#4169E1')  # Blue
            else:
                colors.append('#90EE90')  # Light green
        
        # Create plotly figure
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=df_sorted['name'],
            y=df_sorted[metric],
            marker_color=colors,
            text=df_sorted[metric].round(0),
            textposition='auto',
            hovertemplate='<b>%{x}</b><br>' +
                         f'{metric}: %{{y:.0f}}<br>' +
                         '<extra></extra>'
        ))
        
        # Add average line
        avg_value = df_sorted[metric].mean()
        fig.add_hline(y=avg_value, line_dash="dash", line_color="white",
                     annotation_text=f"Average: {avg_value:.0f}")
        
        # Update layout
        fig.update_layout(
            title=f"{metric} by Facility - {input.sub_district()}",
            xaxis_title="Facility",
            yaxis_title=metric,
            template="plotly_dark",
            showlegend=False,
            xaxis_tickangle=-45,
            height=600
        )
        
        return fig
    
    # Outperformers alert
    @output
    @render.ui
    def outperformers_alert():
        outperformers = current_outperformers()
        
        if not outperformers:
            return ui.div(
                ui.p("✅ No HC/MHC facilities outperforming hospitals in this metric.", 
                     class_="text-success")
            )
        
        alert_content = [
            ui.h5(f"⚠️ Alert: {len(outperformers)} facilities outperforming hospitals", 
                  class_="text-danger"),
            ui.hr()
        ]
        
        for op in outperformers:
            alert_content.append(
                ui.div(
                    ui.strong(f"🔴 {op['name']} ({op['category']})"),
                    ui.br(),
                    f"Value: {op['value']:.0f} | ",
                    f"Hospital min: {op['hospital_min']:.0f} | ",
                    ui.span(f"+{op['percentage']:.1f}%", class_="text-danger fw-bold"),
                    class_="mb-2"
                )
            )
        
        return ui.div(*alert_content)
    
    # Summary statistics
    @output
    @render.ui
    def summary_stats():
        df = filtered_data()
        metric = input.metric()
        
        stats = ui.div(
            ui.tags.dl(
                ui.tags.dt("Total Facilities:"),
                ui.tags.dd(str(len(df))),
                ui.tags.dt("Average:"),
                ui.tags.dd(f"{df[metric].mean():.0f}"),
                ui.tags.dt("Median:"),
                ui.tags.dd(f"{df[metric].median():.0f}"),
                ui.tags.dt("Range:"),
                ui.tags.dd(f"{df[metric].min():.0f} - {df[metric].max():.0f}"),
                ui.tags.dt("Hospitals:"),
                ui.tags.dd(str(len(df[df['facility_category'].isin(['District Hospital', 'Provincial Hospital', 'L2TH'])]))),
                ui.tags.dt("MHCs:"),
                ui.tags.dd(str(len(df[df['facility_category'] == 'Medicalized Health Center']))),
                ui.tags.dt("HCs:"),
                ui.tags.dd(str(len(df[df['facility_category'] == 'Health Center'])))
            ),
            class_="small"
        )
        
        return stats
    
    # District heatmap
    @output
    @render.plot
    def district_heatmap():
        import plotly.express as px
        
        df = facility_data()
        metric = input.metric()
        
        # Aggregate by sub_district
        heatmap_data = df.groupby(['sub_district', 'facility_category'])[metric].mean().reset_index()
        heatmap_pivot = heatmap_data.pivot(index='sub_district', columns='facility_category', values=metric)
        
        fig = px.imshow(
            heatmap_pivot.T,
            labels=dict(x="Sub-District", y="Facility Category", color=metric),
            title=f"Average {metric} by Sub-District and Facility Type",
            color_continuous_scale='RdYlBu_r',
            aspect='auto'
        )
        
        fig.update_layout(
            template="plotly_dark",
            height=700,
            xaxis_tickangle=-45
        )
        
        return fig
    
    # Top outperformers across all districts
    @output
    @render.plot
    def top_outperformers():
        df = facility_data()
        metric = input.metric()
        all_outperformers = []
        
        for sub_dist in df['sub_district'].unique():
            ops = identify_outperformers(df, sub_dist, metric)
            for op in ops:
                op['sub_district'] = sub_dist
                all_outperformers.append(op)
        
        if not all_outperformers:
            fig = go.Figure()
            fig.add_annotation(text="No outperformers found", showarrow=False)
            fig.update_layout(template="plotly_dark")
            return fig
        
        # Convert to DataFrame and get top 20
        op_df = pd.DataFrame(all_outperformers)
        op_df = op_df.nlargest(20, 'percentage')
        
        fig = go.Figure(go.Bar(
            x=op_df['percentage'],
            y=[f"{row['name']}<br>({row['sub_district']})" for _, row in op_df.iterrows()],
            orientation='h',
            marker_color='#FF0000',
            text=op_df['percentage'].round(0).astype(str) + '%',
            textposition='auto'
        ))
        
        fig.update_layout(
            title=f"Top 20 HC/MHC Outperforming Hospitals - {metric}",
            xaxis_title="% Above Hospital",
            yaxis_title="",
            template="plotly_dark",
            height=500,
            margin=dict(l=200)
        )
        
        return fig
    
    # Category comparison
    @output
    @render.plot
    def category_comparison():
        df = facility_data()
        metric = input.metric()
        
        # Calculate averages by category
        cat_avg = df.groupby('facility_category')[metric].agg(['mean', 'median', 'std']).reset_index()
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            name='Mean',
            x=cat_avg['facility_category'],
            y=cat_avg['mean'],
            marker_color='lightblue'
        ))
        
        fig.add_trace(go.Bar(
            name='Median',
            x=cat_avg['facility_category'],
            y=cat_avg['median'],
            marker_color='orange'
        ))
        
        fig.update_layout(
            title=f"Average {metric} by Facility Category",
            xaxis_title="Facility Category",
            yaxis_title=metric,
            template="plotly_dark",
            barmode='group',
            height=500,
            xaxis_tickangle=-45
        )
        
        return fig
    
    # Outperformers table
    @output
    @render.data_frame
    def outperformers_table():
        df = facility_data()
        metric = input.metric()
        all_outperformers = []
        
        for sub_dist in df['sub_district'].unique():
            ops = identify_outperformers(df, sub_dist, metric)
            for op in ops:
                op['sub_district'] = sub_dist
                op['metric'] = metric
                all_outperformers.append(op)
        
        if not all_outperformers:
            return pd.DataFrame({"Message": ["No outperformers found"]})
        
        op_df = pd.DataFrame(all_outperformers)
        op_df = op_df[['sub_district', 'name', 'category', 'value', 'hospital_min', 'difference', 'percentage']]
        op_df.columns = ['Sub-District', 'Facility', 'Category', 'Value', 'Hospital Min', 'Difference', '% Above']
        op_df = op_df.sort_values('% Above', ascending=False)
        op_df = op_df.round(1)
        
        return op_df
    
    # Multi-metric comparison
    @output
    @render.plot
    def multi_metric_comparison():
        df = filtered_data()
        metrics = ['ANC', 'Deliveries', 'Total_OPD', 'Labor_referrals', 'Obstetric_complication_referrals']
        
        # Normalize values for comparison
        df_normalized = df.copy()
        for metric in metrics:
            if df[metric].max() > 0:
                df_normalized[metric + '_norm'] = (df[metric] / df[metric].max()) * 100
        
        # Sort by total OPD
        df_normalized = df_normalized.sort_values('Total_OPD', ascending=False).head(15)
        
        fig = go.Figure()
        
        for metric in metrics:
            if metric + '_norm' in df_normalized.columns:
                fig.add_trace(go.Scatter(
                    x=df_normalized['name'],
                    y=df_normalized[metric + '_norm'],
                    mode='lines+markers',
                    name=metric,
                    line=dict(width=2),
                    marker=dict(size=8)
                ))
        
        fig.update_layout(
            title=f"Multi-Metric Comparison (Normalized) - {input.sub_district()}",
            xaxis_title="Facility",
            yaxis_title="Normalized Value (% of max)",
            template="plotly_dark",
            height=600,
            xaxis_tickangle=-45,
            hovermode='x unified'
        )
        
        return fig
    
    # Scatter analysis
    @output
    @render.plot
    def scatter_analysis():
        df = facility_data()
        
        fig = px.scatter(
            df,
            x='Deliveries',
            y='Total_OPD',
            color='facility_category',
            size='ANC',
            hover_data=['name', 'sub_district'],
            title="Deliveries vs Total OPD (Size = ANC)",
            color_discrete_map={
                'Health Center': '#90EE90',
                'Medicalized Health Center': '#FFD700',
                'District Hospital': '#4169E1',
                'Provincial Hospital': '#4169E1',
                'L2TH': '#4169E1'
            }
        )
        
        fig.update_layout(
            template="plotly_dark",
            height=400
        )
        
        return fig
    
    # Box plot comparison
    @output
    @render.plot
    def box_plot_comparison():
        df = facility_data()
        metric = input.metric()
        
        fig = px.box(
            df,
            x='facility_category',
            y=metric,
            title=f"{metric} Distribution by Facility Category",
            color='facility_category',
            color_discrete_map={
                'Health Center': '#90EE90',
                'Medicalized Health Center': '#FFD700',
                'District Hospital': '#4169E1',
                'Provincial Hospital': '#4169E1',
                'L2TH': '#4169E1'
            }
        )
        
        fig.update_layout(
            template="plotly_dark",
            height=400,
            xaxis_tickangle=-45,
            showlegend=False
        )
        
        return fig

# Create Shiny app
app = App(app_ui, server)

if __name__ == "__main__":
    app.run()