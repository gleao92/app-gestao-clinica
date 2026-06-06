import streamlit as st
import pandas as pd
from supabase import create_client, Client
import urllib.parse
import time
import requests
import os
import bcrypt
from datetime import datetime, timedelta

st.set_page_config(
    page_title="ClinicFlow — Gestão Inteligente",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="auto"
)
