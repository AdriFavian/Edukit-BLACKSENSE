import json
import os
import dash
from dash import dcc, html, dash_table
from dash.dependencies import Output, Input, State
import plotly.graph_objs as go
import paho.mqtt.client as mqtt
from collections import deque
from datetime import datetime
import pandas as pd

# Optional dependency for Excel writing
try:
    from openpyxl import Workbook, load_workbook
except ImportError:
    Workbook = None
    load_workbook = None

# ====== MQTT CONFIG ======
MQTT_BROKER = "broker.hivemq.com"
MQTT_TOPIC = "edukit/suhu"

# ====== DATA BUFFER ======
max_len = 100
timestamps = deque(maxlen=max_len)
data_c, data_f, data_k, data_r = deque(maxlen=max_len), deque(maxlen=max_len), deque(maxlen=max_len), deque(maxlen=max_len)

# ====== KALOR CONFIG ======
C_AIR = 4186  # Kalor jenis air dalam J/kg°C

# ====== STORAGE CONFIG ======
EXCEL_FILE = "data_suhu.xlsx"
EXCEL_HEADERS = ["Waktu", "Celsius", "Fahrenheit", "Kelvin", "Reamur"]

# ====== STORAGE HELPERS ======
def init_excel():
    """Create Excel file with headers if not exists."""
    if Workbook is None or load_workbook is None:
        print("[Excel] openpyxl tidak tersedia. Lewati penyimpanan Excel. Install: pip install openpyxl")
        return
    try:
        if not os.path.exists(EXCEL_FILE):
            wb = Workbook()
            ws = wb.active
            ws.title = "DataSuhu"
            ws.append(EXCEL_HEADERS)
            wb.save(EXCEL_FILE)
            print(f"[Excel] File baru dibuat: {EXCEL_FILE}")
    except Exception as e:
        print("[Excel] Gagal inisialisasi file:", e)

def append_row_to_excel(row):
    """Append one row to Excel file. Row example: [timestamp, C, F, K, R]."""
    if Workbook is None or load_workbook is None:
        return
    try:
        if not os.path.exists(EXCEL_FILE):
            init_excel()
        wb = load_workbook(EXCEL_FILE)
        ws = wb.active
        ws.append(row)
        wb.save(EXCEL_FILE)
    except Exception as e:
        print("[Excel] Gagal menyimpan baris:", e)

# ====== MQTT CALLBACK ======
def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        # Pastikan semua data ada
        if all(key in payload for key in ("C", "F", "K", "R")):
            ts_display = datetime.now().strftime("%H:%M:%S")
            timestamps.append(ts_display)
            data_c.append(payload["C"])
            data_f.append(payload["F"])
            data_k.append(payload["K"])
            data_r.append(payload["R"])
            # Simpan ke Excel
            ts_save = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            append_row_to_excel([ts_save, payload["C"], payload["F"], payload["K"], payload["R"]])
            print(f"[MQTT] Data diterima: {payload}")
    except Exception as e:
        print("Gagal parsing data:", e)

# ====== MQTT CLIENT ======
mqtt_client = mqtt.Client()
mqtt_client.on_message = on_message

try:
    # Pastikan file Excel siap
    init_excel()
    mqtt_client.connect(MQTT_BROKER, 1883, 60)
    mqtt_client.subscribe(MQTT_TOPIC)
    mqtt_client.loop_start()
    print(f"Terhubung ke MQTT Broker: {MQTT_BROKER}, Topic: {MQTT_TOPIC}")
except Exception as e:
    print("Gagal konek MQTT:", e)

# ====== DASH APP ======
app = dash.Dash(__name__)
app.layout = html.Div([
    html.H2("🌡️ BlackSense Smart Thermo EduKit Dashboard", style={'textAlign': 'center', 'marginBottom': '5px'}),
    html.H5("Asas Black Learning - Real-Time Heat Transfer Monitoring", style={'textAlign': 'center', 'color': '#666', 'fontWeight': 'normal', 'marginTop': '0', 'marginBottom': '20px'}),
    html.Div(id='status', style={'textAlign': 'center', 'color': 'gray', 'marginBottom': '20px'}),
    
    # Kontrol dan Card Section
    html.Div([
        # Input Massa
        html.Div([
            html.Label("Masukkan Massa Air (kg):"),
            dcc.Input(
                id='massa-input',
                type='number',
                value=1,  # Nilai default 1 kg
                min=0,
                step=0.01,
                style={'marginLeft': '10px', 'width': '100px'}
            ),
        ], style={'marginBottom': '20px'}),

        # Card Kalor
        html.Div([
            html.Div([
                html.H4("Kalor Diterima", style={'textAlign': 'center'}),
                html.Div(id='kalor-diterima-output', style={'fontSize': '24px', 'textAlign': 'center', 'fontWeight': 'bold'})
            ], style={'border': '1px solid #ddd', 'padding': '20px', 'width': '45%', 'display': 'inline-block', 'margin': '10px'}),
            
            html.Div([
                html.H4("Kalor Dilepas", style={'textAlign': 'center'}),
                html.Div(id='kalor-dilepas-output', style={'fontSize': '24px', 'textAlign': 'center', 'fontWeight': 'bold'})
            ], style={'border': '1px solid #ddd', 'padding': '20px', 'width': '45%', 'display': 'inline-block', 'margin': '10px'})
        ])
    ], style={'textAlign': 'center', 'marginBottom': '30px', 'border': '1px solid #eee', 'padding': '20px', 'width': '80%', 'margin': 'auto'}),
    
    # Grafik Suhu - 2 kolom
    html.Div([
        html.Div([
            dcc.Graph(id='graph-celsius')
        ], style={'width': '48%', 'display': 'inline-block', 'padding': '10px'}),
        
        html.Div([
            dcc.Graph(id='graph-fahrenheit')
        ], style={'width': '48%', 'display': 'inline-block', 'padding': '10px'})
    ]),
    
    html.Div([
        html.Div([
            dcc.Graph(id='graph-kelvin')
        ], style={'width': '48%', 'display': 'inline-block', 'padding': '10px'}),
        
        html.Div([
            dcc.Graph(id='graph-reamur')
        ], style={'width': '48%', 'display': 'inline-block', 'padding': '10px'})
    ]),
    
    html.H4("Tabel Data Real-Time", style={'textAlign': 'center', 'marginTop': '40px'}),
    dash_table.DataTable(
        id='live-table',
        columns=[
            {'name': 'Waktu', 'id': 'waktu'},
            {'name': 'Celsius (°C)', 'id': 'celsius'},
            {'name': 'Fahrenheit (°F)', 'id': 'fahrenheit'},
            {'name': 'Kelvin (K)', 'id': 'kelvin'},
            {'name': 'Reamur (°R)', 'id': 'reamur'},
            {'name': 'Kalor Diterima (J)', 'id': 'kalor_terima'},
            {'name': 'Kalor Dilepas (J)', 'id': 'kalor_lepas'},
        ],
        page_size=15,  # Tampilkan 15 baris per halaman
        style_cell={'textAlign': 'left', 'padding': '5px'},
        style_header={
            'backgroundColor': '#f8f9fa',
            'fontWeight': 'bold',
            'border': '1px solid #dee2e6'
        },
        style_data_conditional=[
            {
                'if': {'row_index': 'odd'},
                'backgroundColor': 'rgb(248, 248, 248)'
            }
        ],
        style_table={'overflowX': 'auto', 'width': '90%', 'margin': 'auto'}
    ),
    html.Button("Export ke Excel", id="btn-export-excel", style={'marginTop': '10px', 'display': 'block', 'margin': 'auto'}),
    dcc.Download(id="download-excel"),
    
    dcc.Interval(id='update', interval=2000, n_intervals=0)
])

@app.callback(
    [Output('graph-celsius', 'figure'),
     Output('graph-fahrenheit', 'figure'),
     Output('graph-kelvin', 'figure'),
     Output('graph-reamur', 'figure'),
     Output('status', 'children'),
     Output('live-table', 'data'),
     Output('kalor-diterima-output', 'children'),
     Output('kalor-dilepas-output', 'children')],
    [Input('update', 'n_intervals'),
     Input('massa-input', 'value')]
)
def update_graph(n, massa):
    if len(data_c) < 2 or massa is None or massa <= 0:
        empty_fig = go.Figure()
        empty_fig.update_layout(title="Menunggu data...")
        status_msg = "Menunggu data dari ESP32 atau masukkan nilai massa yang valid (>0)..."
        kalor_msg = "--- J"
        return empty_fig, empty_fig, empty_fig, empty_fig, status_msg, [], kalor_msg, kalor_msg
    
    # Perhitungan Kalor (Q = m * c * delta_T)
    # delta_T dihitung dari perubahan suhu terakhir untuk menunjukkan perpindahan kalor saat ini
    T_sebelumnya = data_c[-2]
    T_terbaru = data_c[-1]
    delta_T = T_terbaru - T_sebelumnya
    
    Q = massa * C_AIR * delta_T
    
    # Nilai Q diterima = Q dilepas, jadi tampilkan nilai absolut di kedua card
    kalor_pindah = f"{abs(Q):.2f} J"

    # Grafik Celsius
    fig_c = go.Figure()
    fig_c.add_trace(go.Scatter(x=list(timestamps), y=list(data_c), mode='lines+markers', name='Celsius'))
    fig_c.update_layout(
        title="Suhu Celsius (°C)",
        xaxis_title="Waktu",
        yaxis_title="°C",
        template="plotly_white"
    )
    
    # Grafik Fahrenheit
    fig_f = go.Figure()
    fig_f.add_trace(go.Scatter(x=list(timestamps), y=list(data_f), mode='lines+markers', name='Fahrenheit'))
    fig_f.update_layout(
        title="Suhu Fahrenheit (°F)",
        xaxis_title="Waktu",
        yaxis_title="°F",
        template="plotly_white"
    )
    
    # Grafik Kelvin
    fig_k = go.Figure()
    fig_k.add_trace(go.Scatter(x=list(timestamps), y=list(data_k), mode='lines+markers', name='Kelvin'))
    fig_k.update_layout(
        title="Suhu Kelvin (K)",
        xaxis_title="Waktu",
        yaxis_title="K",
        template="plotly_white"
    )
    
    # Grafik Reamur
    fig_r = go.Figure()
    fig_r.add_trace(go.Scatter(x=list(timestamps), y=list(data_r), mode='lines+markers', name='Reamur'))
    fig_r.update_layout(
        title="Suhu Reamur (°R)",
        xaxis_title="Waktu",
        yaxis_title="°R",
        template="plotly_white"
    )
    
    # --- Hitung riwayat kalor untuk tabel ---
    kalor_diterima_history = [0.0] # Entri pertama tidak punya data sebelumnya
    kalor_dilepas_history = [0.0]
    for i in range(1, len(data_c)):
        q_hist_delta_t = data_c[i] - data_c[i-1]
        q_hist = massa * C_AIR * q_hist_delta_t
        if q_hist > 0:
            kalor_diterima_history.append(q_hist)
            kalor_dilepas_history.append(0.0)
        elif q_hist < 0:
            kalor_diterima_history.append(0.0)
            kalor_dilepas_history.append(abs(q_hist))
        else:
            kalor_diterima_history.append(0.0)
            kalor_dilepas_history.append(0.0)

    # Siapkan data untuk tabel, data terbaru di atas
    table_data = [
        {
            'waktu': ts,
            'celsius': c,
            'fahrenheit': f,
            'kelvin': k,
            'reamur': r,
            'kalor_terima': f"{q_terima:.2f}",
            'kalor_lepas': f"{q_lepas:.2f}"
        }
        for ts, c, f, k, r, q_terima, q_lepas in reversed(list(zip(timestamps, data_c, data_f, data_k, data_r, kalor_diterima_history, kalor_dilepas_history)))
    ]
    
    status_text = f"📡 Terhubung ke {MQTT_TOPIC} | Data terakhir: {timestamps[-1]}"
    return fig_c, fig_f, fig_k, fig_r, status_text, table_data, kalor_pindah, kalor_pindah

@app.callback(
    Output("download-excel", "data"),
    Input("btn-export-excel", "n_clicks"),
    State("live-table", "data"),
    prevent_initial_call=True,
)
def export_table_to_excel(n_clicks, table_data):
    if not table_data:
        return
    
    df = pd.DataFrame(table_data)
    return dcc.send_data_frame(df.to_excel, "data_tabel.xlsx", sheet_name="DataSuhu", index=False)

if __name__ == "__main__":
    print("Menjalankan dashboard di http://127.0.0.1:8050")
    app.run(debug=True)
