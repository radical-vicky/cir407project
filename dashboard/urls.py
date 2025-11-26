# urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Main Pages
    path('', views.base, name='base'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('marketplace/', views.marketplace, name='marketplace'),
    path('portfolio/', views.portfolio, name='portfolio'),
    
    # User Management
    path('profile/', views.profile, name='profile'),
    path('payment-methods/', views.payment_methods, name='payment_methods'),
    
    # Wallet & Transactions
    path('wallet/', views.wallet, name='wallet'),
    path('deposit/', views.deposit_funds, name='deposit_funds'),
    path('withdraw/', views.withdraw_funds, name='withdraw_funds'),
    path('wallet/add-funds/', views.add_funds, name='add_funds'),
    path('wallet/transaction-history/', views.transaction_history, name='transaction_history'),
    
    # Analysis & Consultations
    path('purchase_analysis/', views.purchase_analysis, name='purchase_analysis'),
    path('book_consultation/', views.book_consultation, name='book_consultation'),
    path('my-consultations/', views.my_consultations, name='my_consultations'),
    
    # Consultation Management URLs
    path('consultation/<int:consultation_id>/start/', views.start_consultation_session, name='start_consultation'),
    path('consultation/<int:consultation_id>/end/', views.end_consultation_session, name='end_consultation'),
    path('consultation/<int:consultation_id>/cancel/', views.cancel_consultation, name='cancel_consultation'),
    path('consultation/<int:consultation_id>/rate/', views.rate_consultation, name='rate_consultation'),
    
    # Chat URLs
    path('consultation/<int:consultation_id>/chat/', views.consultation_chat, name='consultation_chat'),
    path('consultation/<int:consultation_id>/chat/send/', views.send_chat_message, name='send_chat_message'),
    path('consultation/<int:consultation_id>/chat/messages/', views.get_chat_messages, name='get_chat_messages'),
    path('consultation/<int:consultation_id>/chat/status/', views.update_participant_status, name='update_participant_status'),
    path('consultation/<int:consultation_id>/chat/participants/', views.get_online_participants, name='get_online_participants'),
    
    # Analysis Viewing URLs
    path('analysis/<int:analysis_id>/', views.view_analysis, name='view_analysis_old'),
    path('view-analysis/<int:analysis_id>/', views.view_analysis, name='view_analysis'),
    
    # Market Insights
    path('market-insights/', views.market_insights, name='market_insights'),
    path('market-insights/<int:insight_id>/', views.view_market_insight, name='view_market_insight'),
    
    # Analysis Actions
    path('instant-purchase/', views.instant_purchase, name='instant_purchase'),
    path('check-balance/', views.check_wallet_balance, name='check_balance'),
    path('download-analysis/<int:analysis_id>/', views.download_analysis, name='download_analysis'),
    path('refresh-analysis/<int:analysis_id>/', views.refresh_analysis, name='refresh_analysis'),
    
    # M-Pesa URLs - Deposits & Withdrawals
    path('mpesa/deposit/initiate/', views.initiate_mpesa_deposit, name='initiate_mpesa_deposit'),
    path('mpesa/withdrawal/initiate/', views.initiate_mpesa_withdrawal, name='initiate_mpesa_withdrawal'),
    path('mpesa/callback/', views.mpesa_callback, name='mpesa_callback'),
    path('mpesa/withdrawal/callback/', views.mpesa_withdrawal_callback, name='mpesa_withdrawal_callback'),
    
    # M-Pesa Analysis Purchase URLs
    path('mpesa/purchase-analysis/', views.purchase_analysis_mpesa, name='purchase_analysis_mpesa'),
    path('mpesa/analysis-purchase/callback/', views.mpesa_analysis_purchase_callback, name='mpesa_analysis_purchase_callback'),
    path('mpesa/check-payment-status/<str:checkout_request_id>/', views.check_mpesa_payment_status, name='check_mpesa_payment_status'),
    path('purchase/mpesa/<int:analysis_id>/', views.purchase_analysis_mpesa_view, name='purchase_analysis_mpesa_view'),
    
    # PayPal URLs - Deposits
    path('paypal/deposit/initiate/', views.initiate_paypal_deposit, name='initiate_paypal_deposit'),
    path('paypal/deposit/success/', views.paypal_deposit_success, name='paypal_deposit_success'),
    path('paypal/deposit/cancel/', views.paypal_deposit_cancel, name='paypal_deposit_cancel'),
    
    # PayPal URLs - Analysis Purchases
    path('paypal/purchase/<int:analysis_id>/', views.initiate_paypal_purchase, name='paypal_purchase'),
    path('paypal/purchase/success/', views.paypal_purchase_success, name='paypal_purchase_success'),
    path('paypal/purchase/cancel/', views.paypal_purchase_cancel, name='paypal_purchase_cancel'),
    
    # Transaction and Debug URLs
    path('transaction-status/<int:transaction_id>/', views.check_mpesa_transaction_status, name='check_mpesa_status'),
    path('debug-wallet/', views.debug_wallet, name='debug_wallet'),
    path('debug/withdrawal/', views.debug_withdrawal, name='debug_withdrawal'),
    path('api/analysis/<int:analysis_id>/', views.analysis_detail_api, name='analysis_detail_api'),
]