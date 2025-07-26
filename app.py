import streamlit as st
from pyzbar.pyzbar import decode
import pandas as pd
from datetime import date
from dateutil.relativedelta import relativedelta
import qrcode
from PIL import Image
from io import BytesIO
import plotly.express as px
import numpy as np
import os
import time

class HulkGymQRSystem:
    def __init__(self):
        st.set_page_config(page_title="HULK GYM PRO", layout="wide", page_icon="💪")
        self.excel_path = "gym_data.xlsx"
        self.load_data()
        self.setup_ui()
    
    def load_data(self):
        if os.path.exists(self.excel_path):
            self.df = pd.read_excel(self.excel_path)
            date_cols = ['Start Date', 'End Date']
            for col in date_cols:
                if col in self.df.columns:
                    self.df[col] = pd.to_datetime(self.df[col]).dt.date
        else:
            self.df = pd.DataFrame(columns=[
                'QR Code', 'Count', 'Start Date', 
                'End Date', "Paid", "remaining", "Phone", "Membership Type"
            ])
    
    def save_data(self):
        df_to_save = self.df.copy()
        date_cols = ['Start Date', 'End Date']
        for col in date_cols:
            if col in df_to_save.columns:
                df_to_save[col] = df_to_save[col].astype(str)
        df_to_save.to_excel(self.excel_path, index=False)
    
    def setup_ui(self):
        st.markdown("""
        <style>
            .welcome-message {
                font-size: 42px !important;
                font-weight: bold !important;
                color: #FFD700 !important;
                text-align: center;
                margin: 20px 0;
                text-shadow: 2px 2px 4px #000;
            }
            .stats-card {
                background: linear-gradient(135deg, #1e1e1e, #2a2a2a);
                border-radius: 10px;
                padding: 15px;
                box-shadow: 0 4px 8px rgba(0,0,0,0.2);
                text-align: center;
            }
            .stApp {
                background-color: #121212;
                color: white;
            }
            .stCameraInput > div {
                border-radius: 10px;
                overflow: hidden;
            }
        </style>
        """, unsafe_allow_html=True)
        
        st.title("🏋️ HULK GYM PRO")
        tabs = st.tabs(["📷 Scan Member", "✨ Create Member", "🔄 Renew Subscription", "📊 Analytics"])
        
        with tabs[0]:
            self.scan_qr_tab()
        with tabs[1]:
            self.create_qr_tab()
        with tabs[2]:
            self.renew_tab()
        with tabs[3]:
            self.view_analytics_tab()
    
    def scan_qr_tab(self):
        st.header("🔍 Member Check-In")
        welcome_placeholder = st.empty()
        
        # استخدام st.camera_input بدلاً من cv2.VideoCapture
        img_file = st.camera_input("Scan QR Code", key="qr_scanner")
        
        if img_file is not None:
            try:
                img = Image.open(img_file)
                frame = np.array(img)
                qr_codes = decode(frame)
                
                if qr_codes:
                    for qr in qr_codes:
                        qr_data = qr.data.decode('utf-8').strip()
                        self.process_qr_code(qr_data, welcome_placeholder)
            except Exception as e:
                st.error(f"Error scanning QR: {e}")
    
    def process_qr_code(self, qr_data, welcome_placeholder):
        if qr_data in self.df['QR Code'].values:
            user_row = self.df[self.df['QR Code'] == qr_data].iloc[0]
            end_date = user_row['End Date']
            
            if date.today() <= end_date:
                welcome_html = f"""
                <div class='welcome-message'>
                    <div style='font-size: 48px;'>👋 Welcome</div>
                    <div style='font-size: 56px;'>{qr_data}</div>
                    <div style='font-size: 24px; margin-top: 20px;'>
                        Valid until: <span style='color: #4CAF50;'>{end_date.strftime("%Y-%m-%d")}</span>
                    </div>
                </div>
                """
                welcome_placeholder.markdown(welcome_html, unsafe_allow_html=True)
                self.df.loc[self.df['QR Code'] == qr_data, 'Count'] += 1
                self.save_data()
            else:
                welcome_placeholder.error("❌ Subscription has expired")
        else:
            welcome_placeholder.error("❌ Invalid QR Code")
    
    def create_qr_tab(self):
        st.header("✨ Create New Member")
        
        if 'form_submitted' not in st.session_state:
            st.session_state.form_submitted = False
            st.session_state.form_data = {}
        
        with st.form("create_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                user_name = st.text_input("Member Name", placeholder="Enter full name")
                phone = st.text_input("Phone Number", placeholder="01012345678")
                membership_type = st.selectbox("Membership Type", ["Regular", "Premium", "VIP"])
            
            with col2:
                months = st.radio("Subscription Period", [1, 3, 6, 12], 
                                 format_func=lambda x: f"{x} Month{'s' if x > 1 else ''}")
                paid = st.number_input("Amount Paid", min_value=0, value=300)
                remaining = st.number_input("Remaining Amount", min_value=0, value=0)
            
            if st.form_submit_button("Generate Membership"):
                if user_name:
                    st.session_state.form_submitted = True
                    st.session_state.form_data = {
                        'user_name': user_name,
                        'phone': phone,
                        'membership_type': membership_type,
                        'months': months,
                        'paid': paid,
                        'remaining': remaining
                    }
                else:
                    st.error("Please enter member name")
        
        if st.session_state.get('form_submitted', False):
            form_data = st.session_state.form_data
            qr_image = self.create_member(
                form_data['user_name'],
                form_data['phone'],
                form_data['membership_type'],
                form_data['months'],
                form_data['paid'],
                form_data['remaining']
            )
            
            st.download_button(
                label="⬇️ Download QR Code",
                data=qr_image,
                file_name=f"HULK_GYM_{form_data['user_name']}.png",
                mime="image/png"
            )
    
    def create_member(self, user_name, phone, membership_type, months, paid, remaining):
        start_date = date.today()
        end_date = start_date + relativedelta(months=months)
        
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(user_name)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")
        
        img_bytes = BytesIO()
        qr_img.save(img_bytes, format="PNG")
        img_bytes.seek(0)
        
        new_row = pd.DataFrame({
            'QR Code': [user_name],
            'Count': [0],
            'Start Date': [start_date],
            'End Date': [end_date],
            'Paid': [paid],
            'remaining': [remaining],
            'Phone': [phone],
            'Membership Type': [membership_type]
        })
        self.df = pd.concat([self.df, new_row], ignore_index=True)
        self.save_data()
        
        st.success("🎉 Membership created successfully!")
        
        col1, col2 = st.columns(2)
        with col1:
            st.image(img_bytes, caption=f"QR Code for {user_name}", width=300)
        
        with col2:
            st.markdown(f"""
            ### Member Details
            - **Name**: {user_name}
            - **Phone**: {phone}
            - **Membership Type**: {membership_type}
            - **Start Date**: {start_date}
            - **End Date**: {end_date}
            - **Paid**: {paid} EGP
            - **Remaining**: {remaining} EGP
            """)
        
        return img_bytes.getvalue()
    
    def renew_tab(self):
        st.header("🔄 Renew Membership")
        
        if not self.df.empty:
            member = st.selectbox("Select Member", self.df['QR Code'].unique())
            
            if member:
                user_row = self.df[self.df['QR Code'] == member].iloc[0]
                current_end = user_row['End Date']
                
                st.markdown(f"""
                ### Current Membership Details
                - **Member**: {member}
                - **Phone**: {user_row.get('Phone', 'N/A')}
                - **Membership Type**: {user_row.get('Membership Type', 'Regular')}
                - **Current End Date**: {current_end}
                - **Check-ins**: {user_row['Count']}
                - **Paid Amount**: {user_row['Paid']} EGP
                - **Remaining Amount**: {user_row['remaining']} EGP
                """)
                
                with st.form("renew_form"):
                    months = st.radio("Renewal Period", [1, 3, 6, 12], 
                                     format_func=lambda x: f"{x} Month{'s' if x > 1 else ''}")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        paid = st.number_input("Amount Paid", min_value=0, value=int(user_row['Paid']))
                    with col2:
                        remaining = st.number_input("Remaining Amount", min_value=0, value=int(user_row['remaining']))
                    
                    if st.form_submit_button("💳 Process Renewal"):
                        new_end_date = max(date.today(), current_end) + relativedelta(months=months)
                        
                        self.df.loc[self.df['QR Code'] == member, 'End Date'] = new_end_date
                        self.df.loc[self.df['QR Code'] == member, 'Paid'] = paid
                        self.df.loc[self.df['QR Code'] == member, 'remaining'] = remaining
                        self.save_data()
                        
                        st.success(f"""
                        ✅ Membership for {member} renewed successfully!
                        New end date: {new_end_date}
                        """)
        else:
            st.warning("No members found in database")
    
    def view_analytics_tab(self):
        st.header("📊 Gym Analytics Dashboard")
        
        if not self.df.empty:
            st.subheader("📈 Key Metrics")
            self.display_stats_cards()
            
            st.subheader("📅 Membership Analytics")
            tab1, tab2, tab3 = st.tabs(["Subscriptions", "Check-ins", "Payments"])
            
            with tab1:
                self.plot_subscriptions_chart()
            
            with tab2:
                self.plot_checkins_chart()
            
            with tab3:
                self.plot_payments_chart()
            
            st.subheader("👥 Members Data")
            st.dataframe(self.df, use_container_width=True)
            
            st.download_button(
                label="📤 Export Data to Excel",
                data=self.df.to_csv(index=False).encode('utf-8'),
                file_name="hulk_gym_members.csv",
                mime="text/csv"
            )
        else:
            st.warning("No data available for analytics")
    
    def display_stats_cards(self):
        total_members = len(self.df)
        active_members = len(self.df[self.df['End Date'] >= date.today()])
        expired_members = total_members - active_members
        total_revenue = self.df['Paid'].sum()
        avg_checkins = self.df['Count'].mean()
        
        cols = st.columns(5)
        
        with cols[0]:
            st.markdown(f"""
            <div class='stats-card'>
                <div class='stats-value'>{total_members}</div>
                <div class='stats-label'>Total Members</div>
            </div>
            """, unsafe_allow_html=True)
        
        with cols[1]:
            st.markdown(f"""
            <div class='stats-card'>
                <div class='stats-value' style='color: #4CAF50;'>{active_members}</div>
                <div class='stats-label'>Active Members</div>
            </div>
            """, unsafe_allow_html=True)
        
        with cols[2]:
            st.markdown(f"""
            <div class='stats-card'>
                <div class='stats-value' style='color: #F44336;'>{expired_members}</div>
                <div class='stats-label'>Expired Members</div>
            </div>
            """, unsafe_allow_html=True)
        
        with cols[3]:
            st.markdown(f"""
            <div class='stats-card'>
                <div class='stats-value' style='color: #FFD700;'>{total_revenue} EGP</div>
                <div class='stats-label'>Total Revenue</div>
            </div>
            """, unsafe_allow_html=True)
        
        with cols[4]:
            st.markdown(f"""
            <div class='stats-card'>
                <div class='stats-value'>{avg_checkins:.1f}</div>
                <div class='stats-label'>Avg Check-ins</div>
            </div>
            """, unsafe_allow_html=True)
    
    def plot_subscriptions_chart(self):
        df = self.df.copy()
        df['Month'] = pd.to_datetime(df['Start Date']).dt.to_period('M')
        monthly_data = df.groupby('Month').size().reset_index(name='Count')
        monthly_data['Month'] = monthly_data['Month'].astype(str)
        
        fig = px.bar(monthly_data, x='Month', y='Count', 
                     title="New Memberships by Month",
                     color='Count',
                     color_continuous_scale='thermal')
        fig.update_layout(plot_bgcolor='#1e1e1e', paper_bgcolor='#1e1e1e',
                         font=dict(color='white'))
        st.plotly_chart(fig, use_container_width=True)
    
    def plot_checkins_chart(self):
        df = self.df.sort_values('Count', ascending=False).head(10)
        
        fig = px.bar(df, x='QR Code', y='Count', 
                     title="Top Members by Check-ins",
                     color='Count',
                     color_continuous_scale='viridis')
        fig.update_layout(plot_bgcolor='#1e1e1e', paper_bgcolor='#1e1e1e',
                         font=dict(color='white'))
        st.plotly_chart(fig, use_container_width=True)
    
    def plot_payments_chart(self):
        df = self.df.copy()
        df['Payment Status'] = df.apply(lambda x: "Paid in Full" if x['remaining'] == 0 else "Partial Payment", axis=1)
        
        fig = px.pie(df, names='Payment Status', 
                     title="Payment Status Distribution",
                     hole=0.4,
                     color='Payment Status',
                     color_discrete_map={'Paid in Full':'#4CAF50', 'Partial Payment':'#FFA500'})
        fig.update_layout(plot_bgcolor='#1e1e1e', paper_bgcolor='#1e1e1e',
                         font=dict(color='white'))
        st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    app = HulkGymQRSystem()
