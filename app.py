import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
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


# --- Plot Functions ---
def plot_wrk_metrics(df, title):
    fig, ax1 = plt.subplots(figsize=(10, 5))
    ax1.bar(df.index, df['Requests/sec'], alpha=0.6, label='Requests/sec')
    ax1.set_ylabel("Requests/sec", color='blue')
    ax1.tick_params(axis='y', labelcolor='blue')

    ax2 = ax1.twinx()
    ax2.plot(df.index, df['Avg Latency(ms)'], 'ro-', label='Latency (ms)')
    ax2.set_ylabel("Latency (ms)", color='red')
    ax2.tick_params(axis='y', labelcolor='red')

    plt.title(title)
    st.pyplot(plt)


def plot_dstat_metrics(df, title):
    metrics = ['usr', 'sys', 'idl', 'writ', 'int', 'csw']
    df[metrics].plot(kind='bar', figsize=(12, 6))
    plt.title(title)
    plt.ylabel("Average Value")
    plt.grid(True)
    st.pyplot(plt)


def plot_correlation(df):
    plt.figure(figsize=(10, 6))
    sns.heatmap(df.corr(), annot=True, cmap="coolwarm", fmt=".2f")
    plt.title("Correlation Matrix")
    st.pyplot(plt)


# --- Streamlit UI ---
def main():
    st.title("wrk & dstat Performance Dashboard")
    option = st.selectbox("Select Test Type", ["Blocking", "Non-blocking", "Both"])

    combined_df = load_all_data()

    if option == "Blocking":
        df = combined_df.loc[["Blocking 1KB", "Blocking 8KB"]]
        st.subheader("Blocking: wrk Results")
        plot_wrk_metrics(df, "Blocking - wrk Performance")
        st.subheader("Blocking: System Metrics")
        plot_dstat_metrics(df, "Blocking - dstat Metrics")

    elif option == "Non-blocking":
        df = combined_df.loc[["Non-blocking 1KB", "Non-blocking 8KB"]]
        st.subheader("Non-blocking: wrk Results")
        plot_wrk_metrics(df, "Non-blocking - wrk Performance")
        st.subheader("Non-blocking: System Metrics")
        plot_dstat_metrics(df, "Non-blocking - dstat Metrics")

    elif option == "Both":
        st.subheader("1KB: Blocking vs Non-blocking")
        df_1kb = combined_df.loc[["Blocking 1KB", "Non-blocking 1KB"]]
        plot_wrk_metrics(df_1kb, "1KB - wrk Performance")
        plot_dstat_metrics(df_1kb, "1KB - dstat Metrics")

        st.subheader("8KB: Blocking vs Non-blocking")
        df_8kb = combined_df.loc[["Blocking 8KB", "Non-blocking 8KB"]]
        plot_wrk_metrics(df_8kb, "8KB - wrk Performance")
        plot_dstat_metrics(df_8kb, "8KB - dstat Metrics")

        st.subheader("Correlation Heatmap (All Tests)")
        plot_correlation(combined_df)


if __name__ == "__main__":
    main()
