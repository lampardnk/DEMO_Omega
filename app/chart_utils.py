import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots
import json
import os
from datetime import datetime

def create_activity_chart(activity_data):
    """
    Create an activity chart using Plotly
    
    Args:
        activity_data (list): List of daily submission data
        
    Returns:
        str: HTML div containing the chart
    """
    if not activity_data or len(activity_data) == 0:
        return "<div class='text-center p-4'><p class='text-muted'>No activity data available for the selected time period.</p></div>"
    
    # Sort by date
    sorted_data = sorted(activity_data, key=lambda x: x['date'])
    
    # Extract data points
    dates = [item['date'] for item in sorted_data]
    submissions = [item['unique_successful'] for item in sorted_data]
    percentages = [item['correct_percentage'] for item in sorted_data]
    ratings = [item['avg_rating'] for item in sorted_data]
    
    # Create figure with single y-axis
    fig = go.Figure()
    
    # Add submissions bars
    fig.add_trace(
        go.Bar(
            x=dates,
            y=submissions,
            name="Successful Submissions",
            marker_color='#007bff',
            text=None,  # Remove text on top of bars
            hovertemplate='Date: %{x}<br>Submissions: %{y}<br>Avg Rating: %{customdata:.1f}<extra></extra>',
            customdata=ratings
        )
    )
    
    # Add secondary text (ratings) inside the bars
    for i, (date, submission, rating) in enumerate(zip(dates, submissions, ratings)):
        fig.add_annotation(
            x=date,
            y=submission/2,  # Middle of the bar
            text=f"{rating:.1f}",
            showarrow=False,
            font=dict(
                color="white",
                size=10
            )
        )
    
    # Add percentage line on same y-axis
    # Scale percentages to same range as submissions for display
    max_submissions = max(submissions) if submissions else 10
    scaled_percentages = [p * max_submissions / 100 for p in percentages]
    
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=scaled_percentages,
            name="Correct Percentage",
            marker_color='#28a745',
            line=dict(color='#28a745', width=2),
            mode='lines+markers',
            hovertemplate='Date: %{x}<br>Correct: %{customdata}%<extra></extra>',
            customdata=percentages
        )
    )
    
    # Add figure layout - completely restructured
    fig.update_layout(
        # No title in the figure itself
        height=350,
        margin=dict(l=10, r=10, t=10, b=10),  # Minimal top margin since title is outside
        plot_bgcolor='rgba(248,249,250,1)',
        paper_bgcolor='rgba(0,0,0,0)',
        legend=dict(
            orientation="h",
            y=-0.25,  # Position legend below the chart
            x=0.5,
            xanchor="center"
        ),
        xaxis=dict(
            tickangle=-45,
            title_text="Date",
            tickfont=dict(size=10),
            tickformat="%m-%d"
        ),
        yaxis=dict(
            title_text="Successful Submissions",
            range=[0, max_submissions * 1.2],
            gridcolor='rgba(222,226,230,0.5)'
        ),
        bargap=0.3
    )
    
    # Custom template for shared y-axis
    fig.update_layout(
        yaxis=dict(
            tickmode='array',
            tickvals=[i for i in range(0, int(max_submissions * 1.2) + 1, max(1, int(max_submissions / 5)))],
            ticktext=[str(i) for i in range(0, int(max_submissions * 1.2) + 1, max(1, int(max_submissions / 5)))]
        )
    )
    
    # Convert to HTML and add title outside of the Plotly chart
    config = {
        'displayModeBar': False,
        'responsive': True
    }
    
    chart_html = pio.to_html(fig, full_html=False, config=config, include_plotlyjs='cdn')
    
    # Add HTML title above the chart
    complete_html = f"""
    <div class="chart-container">
        <h4 class="chart-title text-center mb-3">Daily Activity</h4>
        {chart_html}
    </div>
    """
    
    return complete_html

def create_grades_chart(grades_data):
    """
    Create a grades comparison chart using Plotly
    
    Args:
        grades_data (list): List of grade data
        
    Returns:
        str: HTML div containing the chart
    """
    if not grades_data or len(grades_data) == 0:
        return "<div class='text-center p-4'><p class='text-muted'>No grade data available for the selected time period.</p></div>"
    
    # Sort by date
    sorted_data = sorted(grades_data, key=lambda x: x['date'])
    
    # Extract data points
    dates = [item['date'] for item in sorted_data]
    scores = [item['score'] for item in sorted_data]
    medians = [item['class_median'] for item in sorted_data]
    averages = [item['class_average'] for item in sorted_data]
    exam_names = [item['exam_name'] for item in sorted_data]
    
    # Create figure
    fig = go.Figure()
    
    # Add traces for student score, class median, and class average
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=scores,
            name="Your Score",
            mode='lines+markers',
            line=dict(color='#007bff', width=3),
            marker=dict(size=10),
            hovertemplate='Date: %{x}<br>Your Score: %{y}%<extra></extra>'
        )
    )
    
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=medians,
            name="Class Median",
            mode='lines+markers',
            line=dict(color='#6c757d', width=2, dash='dot'),
            marker=dict(size=8),
            hovertemplate='Date: %{x}<br>Class Median: %{y}%<extra></extra>'
        )
    )
    
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=averages,
            name="Class Average",
            mode='lines+markers',
            line=dict(color='#17a2b8', width=2, dash='dash'),
            marker=dict(size=8),
            hovertemplate='Date: %{x}<br>Class Average: %{y}%<extra></extra>'
        )
    )
    
    # Add annotations for exam names
    annotations = []
    for i, exam_name in enumerate(exam_names):
        annotations.append(
            dict(
                x=dates[i],
                y=scores[i],
                text=exam_name,
                showarrow=True,
                arrowhead=0,
                ax=0,
                ay=-40,
                font=dict(size=10)
            )
        )
    
    # Add figure layout - completely restructured
    min_value = min([min(scores), min(medians), min(averages)]) if scores else 0
    fig.update_layout(
        # No title in the figure itself
        height=400,
        margin=dict(l=10, r=10, t=10, b=10),  # Minimal top margin since title is outside
        plot_bgcolor='rgba(248,249,250,1)',
        paper_bgcolor='rgba(0,0,0,0)',
        legend=dict(
            orientation="h",
            y=-0.25,  # Position legend below the chart
            x=0.5,
            xanchor="center"
        ),
        xaxis=dict(
            tickangle=-45,
            title_text="Date",
            tickfont=dict(size=10),
            tickformat="%m-%d"
        ),
        yaxis=dict(
            title_text="Score (%)",
            range=[min_value * 0.9, 100],
            ticksuffix="%",
            gridcolor='rgba(222,226,230,0.5)'
        ),
        annotations=annotations
    )
    
    # Convert to HTML and add title outside of the Plotly chart
    config = {
        'displayModeBar': False,
        'responsive': True
    }
    
    chart_html = pio.to_html(fig, full_html=False, config=config, include_plotlyjs='cdn')
    
    # Add HTML title above the chart
    complete_html = f"""
    <div class="chart-container">
        <h4 class="chart-title text-center mb-3">Grade Comparison</h4>
        {chart_html}
    </div>
    """
    
    return complete_html 