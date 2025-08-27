import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.figure_factory as ff
import re
import os

# --- Utility Functions ---
def parse_wrk_file(filename):
    with open(filename, 'r') as f:
        data = f.read()

    req_sec = float(re.search(r"Requests/sec:\s+([\d.]+)", data).group(1)) if re.search(r"Requests/sec:\s+([\d.]+)", data) else np.nan
    transfer_match = re.search(r"Transfer/sec:\s+([\d.]+)([KMG]?B)", data)
    if transfer_match:
        val = float(transfer_match.group(1))
        unit = transfer_match.group(2)
        if unit == 'KB':
            transfer = val / 1024
        elif unit == 'MB':
            transfer = val
        elif unit == 'GB':
            transfer = val * 1024
        else:
            transfer = val
    else:
        transfer = np.nan

    latency_match = re.search(r"Latency\s+([\d.]+)([mun]?s)", data)
    if latency_match:
        val = float(latency_match.group(1))
        unit = latency_match.group(2)
        if unit == 'ms':
            latency = val
        elif unit == 'us':
            latency = val / 1000
        elif unit == 'ns':
            latency = val / 1e6
        else:
            latency = val
    else:
        latency = np.nan

    return {'Requests/sec': req_sec, 'Transfer(MB/s)': transfer, 'Avg Latency(ms)': latency}


def load_dstat_csv(filename):
    df = pd.read_csv(filename, skiprows=1)
    cols = ['usr', 'sys', 'idl', 'writ', 'int', 'csw']
    cols = [c for c in cols if c in df.columns]
    return df[cols].mean()


# --- Load and Prepare Data ---
def load_all_data():
    labels = ['Blocking 1KB', 'Non-blocking 1KB', 'Blocking 8KB', 'Non-blocking 8KB']
    wrk_files = ['block1kb.txt', 'nonblock1kb.txt', 'block8kb.txt', 'nonblock8kb.txt']
    dstat_files = ['block1kbop.csv', 'nonblock1kbop.csv', 'block8kbop.csv', 'nonblock8kbop.csv']

    wrk_results, dstat_results = {}, {}

    for label, wrk, dstat in zip(labels, wrk_files, dstat_files):
        if os.path.exists(wrk) and os.path.exists(dstat):
            wrk_results[label] = parse_wrk_file(wrk)
            dstat_results[label] = load_dstat_csv(dstat)

    wrk_df = pd.DataFrame(wrk_results).T
    dstat_df = pd.DataFrame(dstat_results).T
    combined_df = pd.concat([wrk_df, dstat_df], axis=1)
    return combined_df


# --- Plot Functions (Plotly) ---
def plot_wrk_metrics_plotly(df, title):
    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=df.index,
        y=df['Requests/sec'],
        name='Requests/sec',
        yaxis='y1'
    ))

    fig.add_trace(go.Scatter(
        x=df.index,
        y=df['Avg Latency(ms)'],
        name='Avg Latency (ms)',
        yaxis='y2',
        mode='lines+markers',
        marker=dict(color='red')
    ))

    fig.update_layout(
        title=title,
        yaxis=dict(title='Requests/sec'),
        yaxis2=dict(
            title='Latency (ms)',
            overlaying='y',
            side='right'
        ),
        barmode='group',
        xaxis=dict(title='Test Case'),
        legend=dict(x=0.01, y=1.1, orientation='h')
    )

    st.plotly_chart(fig, use_container_width=True)


def plot_dstat_metrics_plotly(df, title):
    metrics = ['usr', 'sys', 'idl', 'writ', 'int', 'csw']
    df_metrics = df[metrics]

    fig = go.Figure()
    for col in df_metrics.columns:
        fig.add_trace(go.Bar(
            x=df_metrics.index,
            y=df_metrics[col],
            name=col
        ))

    fig.update_layout(
        title=title,
        barmode='group',
        xaxis_title='Test',
        yaxis_title='Average Value',
        legend_title='Metric'
    )

    st.plotly_chart(fig, use_container_width=True)


def plot_correlation_plotly(df):
    corr = df.corr().round(2)
    z = corr.values
    x = list(corr.columns)
    y = list(corr.index)

    fig = ff.create_annotated_heatmap(
        z,
        x=x,
        y=y,
        colorscale='RdBu',
        showscale=True,
        zmin=-1,
        zmax=1,
        annotation_text=corr.values.round(2),
        hoverinfo="z"
    )

    fig.update_layout(title='Correlation Matrix')
    st.plotly_chart(fig, use_container_width=True)


# --- Streamlit UI ---
def main():
    st.title("wrk & dstat Performance Dashboard (with Plotly)")
    option = st.selectbox("Select Test Type", ["Blocking", "Non-blocking", "Both"])

    combined_df = load_all_data()

    if option == "Blocking":
        df = combined_df.loc[["Blocking 1KB", "Blocking 8KB"]]
        st.subheader("Blocking: wrk Results")
        plot_wrk_metrics_plotly(df, "Blocking - wrk Performance")
        st.subheader("Blocking: System Metrics")
        plot_dstat_metrics_plotly(df, "Blocking - dstat Metrics")

    elif option == "Non-blocking":
        df = combined_df.loc[["Non-blocking 1KB", "Non-blocking 8KB"]]
        st.subheader("Non-blocking: wrk Results")
        plot_wrk_metrics_plotly(df, "Non-blocking - wrk Performance")
        st.subheader("Non-blocking: System Metrics")
        plot_dstat_metrics_plotly(df, "Non-blocking - dstat Metrics")

    elif option == "Both":
        st.subheader("1KB: Blocking vs Non-blocking")
        df_1kb = combined_df.loc[["Blocking 1KB", "Non-blocking 1KB"]]
        plot_wrk_metrics_plotly(df_1kb, "1KB - wrk Performance")
        plot_dstat_metrics_plotly(df_1kb, "1KB - dstat Metrics")

        st.subheader("8KB: Blocking vs Non-blocking")
        df_8kb = combined_df.loc[["Blocking 8KB", "Non-blocking 8KB"]]
        plot_wrk_metrics_plotly(df_8kb, "8KB - wrk Performance")
        plot_dstat_metrics_plotly(df_8kb, "8KB - dstat Metrics")

        st.subheader("Correlation Heatmap (All Tests)")
        plot_correlation_plotly(combined_df)


if __name__ == "__main__":
    main()
