"""
Simplified Health Facility Performance Dashboard
Works with pre-processed facility_summary data
"""

from shiny import App, ui, render, reactive
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pickle
import json

# ====================================================
# DATA LOADING
# ====================================================

def load_facility_data():
    """Load pre-processed facility data"""
    try:
        # Try to load from pickle file first (you can save from notebook)
        with open('facility_summary.pkl', 'rb') as f:
            return pickle.load(f)
    except:
        # Create sample data for demo
        return create_sample_data()

def create_sample_data():
    """Create sample data for demonstration"""
    import numpy as np
    
    # Sample sub-districts and facilities
    sub_districts = ['Shyira Sub District', 'Bushenge Sub District', 'Butaro Sub District']
    facility_types = ['Health Center', 'Medicalized Health Center', 'District Hospital']
    
    data = []
    for sub_dist in sub_districts:
        for i in range(10):
            facility_type = np.random.choice(facility_types, p=[0.7, 0.2, 0.1])
            data.append({
                'sub_district': sub_dist,
                'name': f'Facility_{sub_dist[:3]}_{i+1}',
                'facility_category': facility_type,
                'ANC': np.random.randint(0, 1000),
                'OPD_new': np.random.randint(1000, 50000),
                'OPD_old': np.random.randint(100, 10000),
                'Total_OPD': np.random.randint(1100, 60000),
                'Deliveries': np.random.randint(0, 3000),
                'Labor_referrals': np.random.randint(0, 200),
                'Obstetric_complication_referrals': np.random.randint(0, 150)
            })
    
    return pd.DataFrame(data)

def identify_outperformers(df, sub_district, metric):
    """Identify HC/MHC that outperform hospitals"""
    sub_df = df[df['sub_district'] == sub_district].copy()
    
    hospitals = sub_df[sub_df['facility_category'].isin([
        'District Hospital', 'Provincial Hospital', 'L2TH', 'Teaching Hospital'
    ])]
    
    outperformers = []
    if len(hospitals) > 0 and hospitals[metric].min() > 0:
        min_hospital_value = hospitals[metric].min()
        min_hospital_name = hospitals[hospitals[metric] == min_hospital_value].iloc[0]['name']
        
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
                    'hospital_name': min_hospital_name,
                    'difference': facility[metric] - min_hospital_value,
                    'percentage': ((facility[metric] / min_hospital_value - 1) * 100)
                })
    
    return outperformers

# ====================================================
# UI DEFINITION
# ====================================================

app_ui = ui.page_sidebar(
    ui.sidebar(
        ui.h3("🏥 Health Facility Dashboard", style="color: #2c3e50; margin-bottom: 20px;"),
        ui.hr(),
        
        ui.input_select(
            "sub_district",
            "📍 Select Sub-District:",
            choices=["Loading..."],
            width="100%"
        ),
        
        ui.input_select(
            "metric",
            "📊 Select Metric:",
            choices={
                "ANC": "ANC (Antenatal Care)",
                "OPD_new": "OPD New Cases",
                "OPD_old": "OPD Old Cases",
                "Total_OPD": "Total OPD",
                "Deliveries": "Deliveries",
                "Labor_referrals": "Labor Referrals",
                "Obstetric_complication_referrals": "Obstetric Referrals"
            },
            selected="Total_OPD",
            width="100%"
        ),
        
        ui.input_switch(
            "show_alerts",
            "Show Outperformer Alerts",
            value=True
        ),
        
        ui.input_switch(
            "dark_mode",
            "Dark Mode",
            value=True
        ),
        
        ui.hr(),
        ui.h5("📈 Quick Stats"),
        ui.output_ui("quick_stats"),
        
        width=350,
        bg="#f8f9fa"
    ),
    
    ui.navset_card_tab(
        ui.nav_panel(
            "Main Analysis",
            ui.layout_column_wrap(
                ui.card(
                    ui.card_header("Facility Performance Comparison"),
                    ui.output_plot("main_chart", height="500px"),
                    full_screen=True
                ),
                ui.card(
                    ui.card_header("⚠️ Outperformers Alert"),
                    ui.output_ui("alert_box"),
                    style="background-color: #fff3cd;"
                ),
                width=1
            )
        ),
        
        ui.nav_panel(
            "Heatmap View",
            ui.card(
                ui.card_header("Performance Heatmap Across Sub-Districts"),
                ui.output_plot("heatmap", height="600px"),
                full_screen=True
            )
        ),
        
        ui.nav_panel(
            "Top Performers",
            ui.layout_columns(
                ui.card(
                    ui.card_header("Top 20 Outperformers"),
                    ui.output_plot("top_chart", height="500px")
                ),
                ui.card(
                    ui.card_header("Category Comparison"),
                    ui.output_plot("category_chart", height="500px")
                ),
                col_widths=[6, 6]
            )
        ),
        
        ui.nav_panel(
            "Data Table",
            ui.card(
                ui.card_header("Detailed Outperformers Table"),
                ui.output_data_frame("data_table"),
                full_screen=True
            )
        ),
        
        ui.nav_panel(
            "Multi-Metric",
            ui.card(
                ui.card_header("Multi-Metric Analysis"),
                ui.output_plot("radar_chart", height="500px"),
                full_screen=True
            )
        )
    ),
    
    title="🏥 Rwanda Health Facility Performance Dashboard",
    fillable=True
)

# ====================================================
# SERVER LOGIC
# ====================================================

def server(input, output, session):
    
    # Load data
    @reactive.calc
    def facility_data():
        return load_facility_data()
    
    # Update sub-district choices
    @reactive.effect
    def _():
        df = facility_data()
        choices = sorted(df['sub_district'].unique())
        ui.update_select("sub_district", choices=choices, selected=choices[0])
    
    # Get filtered data
    @reactive.calc
    def filtered_data():
        df = facility_data()
        return df[df['sub_district'] == input.sub_district()]
    
    # Get current outperformers
    @reactive.calc
    def current_outperformers():
        df = facility_data()
        return identify_outperformers(df, input.sub_district(), input.metric())
    
    # Main chart
    @output
    @render.plot
    def main_chart():
        df = filtered_data()
        metric = input.metric()
        outperformers = current_outperformers()
        outperformer_names = [o['name'] for o in outperformers]
        
        # Sort by metric value
        df_sorted = df.sort_values(metric, ascending=False)
        
        # Set colors based on outperformer status
        colors = []
        for _, row in df_sorted.iterrows():
            if row['name'] in outperformer_names:
                colors.append('#FF0000')  # Red
            elif row['facility_category'] == 'Medicalized Health Center':
                colors.append('#FFD700')  # Gold
            elif 'Hospital' in row['facility_category']:
                colors.append('#4169E1')  # Blue
            else:
                colors.append('#90EE90')  # Light green
        
        # Create figure
        fig = go.Figure()
        
        # Add bars
        fig.add_trace(go.Bar(
            x=df_sorted['name'],
            y=df_sorted[metric],
            marker_color=colors,
            text=df_sorted[metric].round(0),
            textposition='auto',
            hovertemplate='<b>%{x}</b><br>' +
                         f'{metric}: %{{y:.0f}}<br>' +
                         'Category: ' + df_sorted['facility_category'] +
                         '<extra></extra>'
        ))
        
        # Add average line
        avg_value = df_sorted[metric].mean()
        fig.add_hline(
            y=avg_value,
            line_dash="dash",
            line_color="white" if input.dark_mode() else "gray",
            annotation_text=f"Average: {avg_value:.0f}"
        )
        
        # Update layout
        template = "plotly_dark" if input.dark_mode() else "plotly_white"
        fig.update_layout(
            title=f"{metric} by Facility - {input.sub_district()}",
            xaxis_title="Facility",
            yaxis_title=metric,
            template=template,
            showlegend=False,
            xaxis_tickangle=-45,
            height=500
        )
        
        return fig
    
    # Alert box
    @output
    @render.ui
    def alert_box():
        if not input.show_alerts():
            return ui.div("Alerts disabled")
        
        outperformers = current_outperformers()
        
        if not outperformers:
            return ui.div(
                ui.h5("✅ No Anomalies Detected", style="color: green;"),
                ui.p("No HC/MHC facilities are outperforming hospitals in this metric."),
                style="padding: 10px;"
            )
        
        alert_items = [
            ui.h5(f"⚠️ {len(outperformers)} Facilities Outperforming Hospitals", 
                  style="color: red;"),
            ui.hr()
        ]
        
        for op in outperformers[:5]:  # Show top 5
            alert_items.append(
                ui.div(
                    ui.strong(f"🔴 {op['name']}"),
                    ui.br(),
                    f"Type: {op['category']}",
                    ui.br(),
                    f"Value: {op['value']:.0f} (Hospital min: {op['hospital_min']:.0f})",
                    ui.br(),
                    ui.span(f"Outperforms by: +{op['percentage']:.1f}%", 
                           style="color: red; font-weight: bold;"),
                    style="margin-bottom: 10px; padding: 5px; background-color: #ffe6e6; border-radius: 5px;"
                )
            )
        
        if len(outperformers) > 5:
            alert_items.append(
                ui.p(f"... and {len(outperformers) - 5} more", style="font-style: italic;")
            )
        
        return ui.div(*alert_items, style="padding: 10px;")
    
    # Quick stats
    @output
    @render.ui
    def quick_stats():
        df = filtered_data()
        metric = input.metric()
        outperformers = current_outperformers()
        
        return ui.div(
            ui.tags.style("""
                .stat-item {
                    display: flex;
                    justify-content: space-between;
                    padding: 5px 0;
                    border-bottom: 1px solid #e0e0e0;
                }
                .stat-value {
                    font-weight: bold;
                    color: #2c3e50;
                }
            """),
            ui.div(
                ui.span("Total Facilities:"),
                ui.span(str(len(df)), class_="stat-value"),
                class_="stat-item"
            ),
            ui.div(
                ui.span("Hospitals:"),
                ui.span(str(len(df[df['facility_category'].str.contains('Hospital')])), 
                       class_="stat-value"),
                class_="stat-item"
            ),
            ui.div(
                ui.span("Health Centers:"),
                ui.span(str(len(df[df['facility_category'] == 'Health Center'])), 
                       class_="stat-value"),
                class_="stat-item"
            ),
            ui.div(
                ui.span("MHCs:"),
                ui.span(str(len(df[df['facility_category'] == 'Medicalized Health Center'])), 
                       class_="stat-value"),
                class_="stat-item"
            ),
            ui.div(
                ui.span("Outperformers:"),
                ui.span(str(len(outperformers)), 
                       class_="stat-value", style="color: red;" if outperformers else ""),
                class_="stat-item"
            ),
            ui.div(
                ui.span(f"{metric} Average:"),
                ui.span(f"{df[metric].mean():.0f}", class_="stat-value"),
                class_="stat-item"
            )
        )
    
    # Heatmap
    @output
    @render.plot
    def heatmap():
        df = facility_data()
        metric = input.metric()
        
        # Create pivot table
        heatmap_data = df.groupby(['sub_district', 'facility_category'])[metric].mean().reset_index()
        heatmap_pivot = heatmap_data.pivot(
            index='sub_district',
            columns='facility_category',
            values=metric
        )
        
        fig = px.imshow(
            heatmap_pivot.T,
            labels=dict(x="Sub-District", y="Facility Type", color=metric),
            title=f"Average {metric} Heatmap",
            color_continuous_scale='RdYlBu_r',
            aspect='auto'
        )
        
        template = "plotly_dark" if input.dark_mode() else "plotly_white"
        fig.update_layout(
            template=template,
            height=600,
            xaxis_tickangle=-45
        )
        
        return fig
    
    # Top performers chart
    @output
    @render.plot
    def top_chart():
        df = facility_data()
        metric = input.metric()
        all_outperformers = []
        
        # Get all outperformers across districts
        for sub_dist in df['sub_district'].unique():
            ops = identify_outperformers(df, sub_dist, metric)
            for op in ops:
                op['sub_district'] = sub_dist
                all_outperformers.append(op)
        
        if not all_outperformers:
            fig = go.Figure()
            fig.add_annotation(
                text="No outperformers found across all sub-districts",
                showarrow=False,
                font=dict(size=20)
            )
            template = "plotly_dark" if input.dark_mode() else "plotly_white"
            fig.update_layout(template=template, height=500)
            return fig
        
        # Convert to DataFrame and get top 20
        op_df = pd.DataFrame(all_outperformers)
        op_df = op_df.nlargest(20, 'percentage')
        
        fig = go.Figure(go.Bar(
            x=op_df['percentage'],
            y=[f"{row['name']}<br>({row['sub_district'][:15]}...)" 
               for _, row in op_df.iterrows()],
            orientation='h',
            marker_color='#FF0000',
            text=op_df['percentage'].round(0).astype(str) + '%',
            textposition='auto',
            hovertemplate='%{y}<br>Outperforms by: %{x:.1f}%<extra></extra>'
        ))
        
        template = "plotly_dark" if input.dark_mode() else "plotly_white"
        fig.update_layout(
            title=f"Top 20 Outperformers - {metric}",
            xaxis_title="% Above Hospital Minimum",
            yaxis_title="",
            template=template,
            height=500,
            margin=dict(l=200)
        )
        
        return fig
    
    # Category comparison
    @output
    @render.plot
    def category_chart():
        df = facility_data()
        metric = input.metric()
        
        # Calculate statistics by category
        cat_stats = df.groupby('facility_category')[metric].agg([
            'mean', 'median', 'std', 'count'
        ]).reset_index()
        
        fig = go.Figure()
        
        # Add mean bars
        fig.add_trace(go.Bar(
            name='Average',
            x=cat_stats['facility_category'],
            y=cat_stats['mean'],
            marker_color='lightblue',
            text=cat_stats['mean'].round(0),
            textposition='auto'
        ))
        
        # Add median bars
        fig.add_trace(go.Bar(
            name='Median',
            x=cat_stats['facility_category'],
            y=cat_stats['median'],
            marker_color='orange',
            text=cat_stats['median'].round(0),
            textposition='auto'
        ))
        
        template = "plotly_dark" if input.dark_mode() else "plotly_white"
        fig.update_layout(
            title=f"{metric} by Facility Category",
            xaxis_title="Facility Category",
            yaxis_title=metric,
            template=template,
            barmode='group',
            height=500,
            xaxis_tickangle=-45
        )
        
        return fig
    
    # Data table
    @output
    @render.data_frame
    def data_table():
        df = facility_data()
        metric = input.metric()
        all_outperformers = []
        
        # Collect all outperformers
        for sub_dist in df['sub_district'].unique():
            ops = identify_outperformers(df, sub_dist, metric)
            for op in ops:
                all_outperformers.append({
                    'Sub-District': sub_dist,
                    'Facility': op['name'],
                    'Type': op['category'],
                    f'{metric} Value': op['value'],
                    'Hospital Min': op['hospital_min'],
                    'Hospital Name': op['hospital_name'],
                    'Difference': op['difference'],
                    '% Above': f"{op['percentage']:.1f}%"
                })
        
        if not all_outperformers:
            return pd.DataFrame({"Message": ["No outperformers found"]})
        
        result_df = pd.DataFrame(all_outperformers)
        result_df = result_df.sort_values('% Above', ascending=False)
        
        return result_df
    
    # Radar chart for multi-metric comparison
    @output
    @render.plot
    def radar_chart():
        df = filtered_data()
        
        # Select top 5 facilities by Total_OPD
        top_facilities = df.nlargest(5, 'Total_OPD')
        
        # Metrics to include
        metrics = ['ANC', 'Deliveries', 'Total_OPD', 'Labor_referrals', 
                  'Obstetric_complication_referrals']
        
        fig = go.Figure()
        
        for _, facility in top_facilities.iterrows():
            # Normalize values (0-100 scale)
            values = []
            for metric in metrics:
                max_val = df[metric].max()
                if max_val > 0:
                    values.append((facility[metric] / max_val) * 100)
                else:
                    values.append(0)
            
            fig.add_trace(go.Scatterpolar(
                r=values,
                theta=metrics,
                fill='toself',
                name=facility['name'][:20]
            ))
        
        template = "plotly_dark" if input.dark_mode() else "plotly_white"
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 100]
                )
            ),
            title=f"Multi-Metric Comparison - Top 5 Facilities in {input.sub_district()}",
            template=template,
            height=500,
            showlegend=True
        )
        
        return fig

# Create app
app = App(app_ui, server)

if __name__ == "__main__":
    print("Starting Health Facility Dashboard...")
    print("Dashboard will be available at: http://127.0.0.1:8000")
    app.run()