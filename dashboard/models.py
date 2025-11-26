from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
import os
import uuid
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta
import random
import string
import logging

# Set up logger
logger = logging.getLogger(__name__)

def user_profile_picture_path(instance, filename):
    # File will be uploaded to MEDIA_ROOT/profile_pics/user_<id>/<filename>
    ext = filename.split('.')[-1]
    filename = f"profile_picture_{instance.user.id}.{ext}"
    return os.path.join('profile_pics', f"user_{instance.user.id}", filename)

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    profile_picture = models.ImageField(
        upload_to=user_profile_picture_path, 
        blank=True, 
        null=True
    )
    date_of_birth = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"

    @property
    def full_name(self):
        return f"{self.user.first_name} {self.user.last_name}".strip() or self.user.username


class UserWallet(models.Model):
    PAYMENT_METHODS = [
        ('mpesa', 'M-Pesa'),
        ('paypal', 'PayPal'),
        ('bank', 'Bank Transfer'),
        ('crypto', 'Cryptocurrency'),
        ('wallet', 'Wallet Balance'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    wallet_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    
    # Payment Methods
    mpesa_number = models.CharField(max_length=15, blank=True, null=True)
    mpesa_verified = models.BooleanField(default=False)
    
    paypal_email = models.EmailField(blank=True, null=True)
    paypal_verified = models.BooleanField(default=False)
    
    preferred_payment_method = models.CharField(
        max_length=10, 
        choices=PAYMENT_METHODS, 
        default='mpesa'
    )
    
    # Transaction limits
    daily_deposit_limit = models.DecimalField(max_digits=10, decimal_places=2, default=10000.00)
    daily_withdrawal_limit = models.DecimalField(max_digits=10, decimal_places=2, default=5000.00)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Wallet"

    def get_balance_display(self):
        return f"${self.balance:,.2f}"

    def can_deposit(self, amount):
        return amount <= self.daily_deposit_limit

    def can_withdraw(self, amount):
        return amount <= self.balance and amount <= self.daily_withdrawal_limit
    
    def can_afford_consultation(self, consultation_price):
        """Check if user has enough balance for a consultation"""
        return self.balance >= consultation_price
    
    def deduct_for_consultation(self, consultation_price):
        """Deduct amount for consultation purchase"""
        if self.can_afford_consultation(consultation_price):
            self.balance -= consultation_price
            self.save()
            return True
        return False
    
    def add_funds(self, amount):
        """Add funds to wallet"""
        self.balance += amount
        self.save()
        return True

    @property
    def total_withdrawn(self):
        """Calculate total amount withdrawn by user"""
        from django.db.models import Sum
        result = Transaction.objects.filter(
            user=self.user,
            transaction_type='withdrawal',
            status='completed'
        ).aggregate(total=Sum('amount'))
        return result['total'] or Decimal('0.00')


# Define transaction choices before Transaction model
TRANSACTION_TYPES = [
    ('deposit', 'Deposit'),
    ('withdrawal', 'Withdrawal'),
    ('purchase', 'Purchase'),
    ('refund', 'Refund'),
    ('commission', 'Commission'),
]

TRANSACTION_STATUS = [
    ('pending', 'Pending'),
    ('completed', 'Completed'),
    ('failed', 'Failed'),
    ('cancelled', 'Cancelled'),
]


class Transaction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    payment_method = models.CharField(max_length=20, choices=UserWallet.PAYMENT_METHODS)
    status = models.CharField(max_length=20, choices=TRANSACTION_STATUS, default='pending')
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Add transaction_id field that was referenced in admin
    transaction_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    
    # Add these missing fields:
    reference = models.CharField(max_length=100, blank=True, null=True)  # For M-Pesa reference
    mpesa_code = models.CharField(max_length=100, blank=True, null=True)  # For M-Pesa transaction code
    paypal_transaction_id = models.CharField(max_length=100, blank=True, null=True)
    
    # If you have analysis and consultation foreign keys:
    analysis = models.ForeignKey('CryptoAnalysis', on_delete=models.SET_NULL, null=True, blank=True)
    consultation = models.ForeignKey('Consultation', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Add updated_at field that was referenced in admin
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.transaction_type} - ${self.amount}"
    
    class Meta:
        ordering = ['-created_at']
    
    @property
    def is_successful(self):
        return self.status == 'completed'
    
    @property
    def is_pending(self):
        return self.status == 'pending'


class Analyst(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(blank=True, null=True)
    experience_years = models.IntegerField(default=0)
    specialization = models.CharField(max_length=200, blank=True, null=True)
    verified = models.BooleanField(default=False)
    total_sales = models.IntegerField(default=0)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    joined_date = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)
    # Consultation availability
    available_for_consultation = models.BooleanField(default=True)
    consultation_hours = models.JSONField(default=dict, blank=True, null=True)  # Store availability schedule
    
    def __str__(self):
        return f"Analyst: {self.user.username}"
    
    @property
    def analyst_name(self):
        return f"{self.user.first_name} {self.user.last_name}".strip() or self.user.username
    
    @property
    def analyst_initials(self):
        if self.user.first_name and self.user.last_name:
            return f"{self.user.first_name[0]}{self.user.last_name[0]}".upper()
        return self.user.username[:2].upper()
    
    @property
    def total_revenue(self):
        """Calculate total revenue from all analyses"""
        from django.db.models import Sum
        result = CryptoAnalysis.objects.filter(
            analyst=self
        ).aggregate(total=Sum('total_revenue'))
        return result['total'] or Decimal('0.00')


class CryptoAnalysis(models.Model):
    ANALYSIS_TYPES = [
        ('technical', 'Technical Analysis'),
        ('fundamental', 'Fundamental Analysis'),
        ('trading', 'Trading Signals'),
        ('market', 'Market Research'),
    ]
    
    RISK_LEVELS = [
        ('low', 'Low Risk'),
        ('medium', 'Medium Risk'),
        ('high', 'High Risk'),
    ]
    
    TIMEFRAMES = [
        ('short_term', 'Short Term (1-7 days)'),
        ('medium_term', 'Medium Term (1-4 weeks)'),
        ('long_term', 'Long Term (1-6 months)'),
    ]
    
    RECOMMENDATIONS = [
        ('buy', 'Buy'),
        ('sell', 'Sell'),
        ('hold', 'Hold'),
        ('strong_buy', 'Strong Buy'),
        ('strong_sell', 'Strong Sell'),
    ]
    
    CHART_TYPES = [
        ('line', 'Line Chart'),
        ('candlestick', 'Candlestick Chart'),
        ('area', 'Area Chart'),
        ('technical', 'Technical Analysis Chart'),
    ]
    
    # Basic Information
    title = models.CharField(max_length=200)
    cryptocurrency = models.CharField(max_length=100)
    symbol = models.CharField(max_length=10)
    analyst = models.ForeignKey(Analyst, on_delete=models.CASCADE)
    
    # Analysis Details
    analysis_type = models.CharField(max_length=20, choices=ANALYSIS_TYPES)
    timeframe = models.CharField(max_length=20, choices=TIMEFRAMES)
    risk_level = models.CharField(max_length=10, choices=RISK_LEVELS)
    recommendation = models.CharField(max_length=15, choices=RECOMMENDATIONS, default='hold')
    
    # Interactive Chart Fields
    chart_type = models.CharField(max_length=20, choices=CHART_TYPES, default='candlestick')
    chart_data = models.JSONField(default=dict, blank=True, null=True, help_text="JSON data for interactive charts")
    chart_config = models.JSONField(default=dict, blank=True, null=True, help_text="Chart styling and configuration")
    
    # Technical Analysis Data
    technical_indicators_json = models.JSONField(default=dict, blank=True, null=True, help_text="Technical indicators configuration")
    support_levels = models.JSONField(default=list, blank=True, null=True)
    resistance_levels = models.JSONField(default=list, blank=True, null=True)
    
    # Pricing
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    is_featured = models.BooleanField(default=False)
    discount_percentage = models.IntegerField(default=0)
    total_revenue = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    
    # Content
    description = models.TextField()
    executive_summary = models.TextField()
    preview_content = models.TextField(help_text="Content shown in preview mode")
    full_content = models.TextField(help_text="Full analysis content for purchasers")
    
    # Technical Analysis Fields
    chart_patterns = models.JSONField(default=list, blank=True, null=True)
    price_targets = models.JSONField(default=dict, blank=True, null=True)
    
    # Fundamental Analysis Fields
    fundamental_analysis = models.JSONField(default=dict, blank=True, null=True)
    
    # Trading Strategy
    trading_strategy = models.JSONField(default=dict, blank=True, null=True)
    
    # Risk Management
    risk_management_note = models.TextField(blank=True, null=True, help_text="Risk management advice")
    
    # Bullish and Bearish Scenarios
    bullish_recommendation = models.JSONField(default=dict, blank=True, null=True)
    bearish_recommendation = models.JSONField(default=dict, blank=True, null=True)
    
    # Scoring and Ratings
    overall_score = models.DecimalField(max_digits=3, decimal_places=1, default=8.0, help_text="Overall score out of 10")
    growth_potential = models.CharField(max_length=20, default="+24%", help_text="Expected growth percentage")
    
    # Metadata
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    sales_count = models.IntegerField(default=0)
    views_count = models.IntegerField(default=0)
    
    # Status
    is_active = models.BooleanField(default=True)
    is_premium = models.BooleanField(default=True)
    
    # Chart Image (fallback)
    chart_image = models.ImageField(upload_to='analysis_charts/', blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.cryptocurrency} ({self.symbol}) - {self.analysis_type}"
    
    @property
    def final_price(self):
        if self.discount_percentage > 0:
            discount_amount = (self.price * self.discount_percentage) / 100
            return self.price - discount_amount
        return self.price
    
    @property
    def is_new(self):
        return self.created_at > timezone.now() - timedelta(days=7)
    
    @property
    def features_list(self):
        """Convert features JSON to list for templates"""
        default_features = [
            "Detailed technical analysis",
            "Price targets and entry points",
            "Risk management strategy",
            "Market sentiment analysis",
            "Support and resistance levels",
            "Interactive charts with annotations"
        ]
        return self.trading_strategy.get('features', default_features) if self.trading_strategy else default_features
    
    @property
    def recommendation_icon(self):
        icons = {
            'buy': 'arrow-up',
            'sell': 'arrow-down',
            'hold': 'pause',
            'strong_buy': 'arrow-up',
            'strong_sell': 'arrow-down'
        }
        return icons.get(self.recommendation, 'pause')
    
    @property
    def has_interactive_charts(self):
        """Check if analysis has interactive chart data"""
        return bool(self.chart_data) or self.chart_annotations.exists() or self.indicator_data.exists()
    
    def get_default_chart_data(self):
        """Generate default chart data if none exists"""
        if not self.chart_data:
            # Generate sample price data
            base_price = 27000
            data_points = 30
            prices = []
            timestamps = []
            
            current_time = timezone.now() - timedelta(days=30)
            
            for i in range(data_points):
                timestamps.append(current_time.isoformat())
                # Generate realistic price movement
                change = (random.random() - 0.5) * 0.1  # ±5% change
                price = base_price * (1 + change) if prices else base_price
                prices.append(float(price))
                current_time += timedelta(days=1)
            
            self.chart_data = {
                'timestamps': timestamps,
                'prices': prices,
                'timeframe': '1M'
            }
            self.save()
        
        return self.chart_data
    
    def update_sales_count(self):
        """Update sales count from purchases"""
        self.sales_count = self.purchasedanalysis_set.count()
        self.save()
    
    class Meta:
        verbose_name_plural = "Crypto Analyses"
        ordering = ['-created_at']


class MarketInsight(models.Model):
    """Model for market insights and trends"""
    INSIGHT_TYPES = [
        ('market_trend', 'Market Trend'),
        ('price_analysis', 'Price Analysis'),
        ('regulatory', 'Regulatory Update'),
        ('technology', 'Technology Update'),
        ('adoption', 'Adoption News'),
        ('security', 'Security Alert'),
    ]
    
    URGENCY_LEVELS = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    # Basic Information
    title = models.CharField(max_length=200)
    insight_type = models.CharField(max_length=20, choices=INSIGHT_TYPES, default='market_trend')
    cryptocurrency = models.CharField(max_length=100, blank=True, null=True)
    symbol = models.CharField(max_length=10, blank=True, null=True)
    
    # Content
    summary = models.TextField(help_text="Brief summary of the insight")
    full_content = models.TextField(help_text="Detailed insight content")
    key_takeaways = models.TextField(help_text="Key points from the insight", blank=True)
    
    # Impact and Urgency
    impact_level = models.CharField(max_length=10, choices=URGENCY_LEVELS, default='medium')
    urgency = models.CharField(max_length=10, choices=URGENCY_LEVELS, default='medium')
    potential_impact = models.TextField(help_text="Potential market impact", blank=True)
    
    # Source and Verification
    source = models.CharField(max_length=200, blank=True, null=True)
    source_url = models.URLField(blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(Analyst, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Metadata
    views_count = models.IntegerField(default=0)
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    # Timestamps
    published_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.title} - {self.get_insight_type_display()}"
    
    @property
    def is_recent(self):
        """Check if insight was published in the last 24 hours"""
        return self.published_at > timezone.now() - timedelta(hours=24)
    
    @property
    def urgency_color(self):
        """Get color for urgency level"""
        colors = {
            'low': 'green',
            'medium': 'orange',
            'high': 'red',
            'critical': 'darkred'
        }
        return colors.get(self.urgency, 'gray')
    
    @property
    def impact_color(self):
        """Get color for impact level"""
        colors = {
            'low': 'blue',
            'medium': 'orange',
            'high': 'red',
            'critical': 'darkred'
        }
        return colors.get(self.impact_level, 'gray')
    
    def increment_views(self):
        """Increment view count"""
        self.views_count += 1
        self.save()
    
    class Meta:
        ordering = ['-published_at', '-created_at']
        verbose_name = 'Market Insight'
        verbose_name_plural = 'Market Insights'


class ChartAnnotation(models.Model):
    """Model for chart annotations and markers"""
    ANALYSIS_TYPES = [
        ('support', 'Support Level'),
        ('resistance', 'Resistance Level'),
        ('entry', 'Entry Point'),
        ('exit', 'Exit Point'),
        ('trend', 'Trend Line'),
        ('pattern', 'Chart Pattern'),
        ('target', 'Price Target'),
        ('stop_loss', 'Stop Loss'),
    ]
    
    analysis = models.ForeignKey(CryptoAnalysis, on_delete=models.CASCADE, related_name='chart_annotations')
    type = models.CharField(max_length=20, choices=ANALYSIS_TYPES)
    price_level = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    timestamp = models.DateTimeField(null=True, blank=True)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, default='#f0b90b')  # Hex color
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.type} - {self.analysis.cryptocurrency}"
    
    class Meta:
        ordering = ['price_level']


class TechnicalIndicatorData(models.Model):
    """Model for technical indicators data"""
    INDICATOR_TYPES = [
        ('sma', 'Simple Moving Average'),
        ('ema', 'Exponential Moving Average'),
        ('rsi', 'Relative Strength Index'),
        ('macd', 'Moving Average Convergence Divergence'),
        ('bollinger', 'Bollinger Bands'),
        ('stochastic', 'Stochastic Oscillator'),
        ('volume', 'Volume'),
    ]
    
    analysis = models.ForeignKey(CryptoAnalysis, on_delete=models.CASCADE, related_name='indicator_data')
    indicator_type = models.CharField(max_length=20, choices=INDICATOR_TYPES)
    data = models.JSONField(default=dict, help_text="Indicator data points")
    parameters = models.JSONField(default=dict, help_text="Indicator parameters (periods, etc.)")
    color = models.CharField(max_length=7, default='#03a66d')  # Hex color
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.get_indicator_type_display()} - {self.analysis.cryptocurrency}"


class AnalysisInsight(models.Model):
    """Model for individual insights within an analysis"""
    analysis = models.ForeignKey(CryptoAnalysis, on_delete=models.CASCADE, related_name='insights')
    title = models.CharField(max_length=200)
    description = models.TextField()
    importance = models.CharField(max_length=10, choices=[
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ], default='medium')
    category = models.CharField(max_length=50, choices=[
        ('technical', 'Technical'),
        ('fundamental', 'Fundamental'),
        ('sentiment', 'Market Sentiment'),
        ('risk', 'Risk Assessment'),
        ('opportunity', 'Trading Opportunity'),
    ], default='technical')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.title} - {self.analysis.cryptocurrency}"
    
    class Meta:
        ordering = ['-importance', 'created_at']


class AnalysisMetric(models.Model):
    """Model for detailed metrics in analysis"""
    analysis = models.ForeignKey(CryptoAnalysis, on_delete=models.CASCADE, related_name='metrics')
    name = models.CharField(max_length=100)
    current_value = models.CharField(max_length=50)
    previous_value = models.CharField(max_length=50)
    change = models.CharField(max_length=20)
    trend = models.CharField(max_length=10, choices=[
        ('up', 'Up'),
        ('down', 'Down'),
        ('neutral', 'Neutral'),
    ], default='neutral')
    unit = models.CharField(max_length=20, blank=True)
    description = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.name} - {self.analysis.cryptocurrency}"
    
    class Meta:
        ordering = ['name']


class PurchasedAnalysis(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    analysis = models.ForeignKey(CryptoAnalysis, on_delete=models.CASCADE)
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2)
    purchased_at = models.DateTimeField(auto_now_add=True)
    access_expires = models.DateTimeField(blank=True, null=True)
    rating_given = models.IntegerField(blank=True, null=True)
    review = models.TextField(blank=True, null=True)
    
    class Meta:
        unique_together = ['user', 'analysis']
        ordering = ['-purchased_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.analysis.cryptocurrency}"
    
    @property
    def is_expired(self):
        if self.access_expires:
            return timezone.now() > self.access_expires
        return False
    
    @property
    def days_remaining(self):
        """Get days remaining until access expires"""
        if self.access_expires:
            remaining = self.access_expires - timezone.now()
            return max(0, remaining.days)
        return None
    
    def save(self, *args, **kwargs):
        # Set access expiry to 30 days from purchase if not set
        if not self.access_expires:
            self.access_expires = timezone.now() + timedelta(days=30)
        super().save(*args, **kwargs)


class AnalysisRating(models.Model):
    analysis = models.ForeignKey(CryptoAnalysis, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    review = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['analysis', 'user']
    
    def __str__(self):
        return f"{self.rating}/5 - {self.analysis.cryptocurrency}"


class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    icon = models.CharField(max_length=50, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name
    
    @property
    def analyses_count(self):
        return self.cryptoanalysis_set.count()


class ConsultationPackage(models.Model):
    LEVEL_CHOICES = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
        ('expert', 'Expert'),
    ]
    
    title = models.CharField(max_length=200)
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default='beginner')
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    features = models.TextField(help_text="Enter each feature on a new line")
    icon_class = models.CharField(max_length=50, default='chart-line')
    duration_minutes = models.IntegerField(default=60, help_text="Duration in minutes")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['price']
        verbose_name = 'Consultation Package'
        verbose_name_plural = 'Consultation Packages'
    
    def __str__(self):
        return f"{self.title} - ${self.price}"
    
    def get_features_list(self):
        """Convert features text to list"""
        if self.features:
            return [feature.strip() for feature in self.features.split('\n') if feature.strip()]
        return []
    
    def get_level_display(self):
        return dict(self.LEVEL_CHOICES).get(self.level, self.level)


class Consultation(models.Model):
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('no_show', 'No Show'),
    ]
    
    LEVEL_CHOICES = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
        ('expert', 'Expert'),
    ]
    
    PAYMENT_METHODS = [
        ('wallet', 'Wallet Balance'),
        ('mpesa', 'M-Pesa'),
        ('paypal', 'PayPal'),
        ('bank', 'Bank Transfer'),
    ]
    
    MEETING_PLATFORMS = [
        ('jitsi', 'Jitsi Meet'),
        ('zoom', 'Zoom'),
        ('google_meet', 'Google Meet'),
        ('teams', 'Microsoft Teams'),
        ('custom', 'Custom Link'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default='beginner')
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    duration_minutes = models.IntegerField(default=60)
    scheduled_date = models.DateTimeField()
    
    # Video Consultation Fields
    meeting_platform = models.CharField(max_length=20, choices=MEETING_PLATFORMS, default='jitsi')
    meeting_link = models.URLField(blank=True, null=True)
    meeting_id = models.CharField(max_length=100, blank=True, null=True)
    meeting_password = models.CharField(max_length=100, blank=True, null=True)
    join_url = models.URLField(blank=True, null=True)
    
    # Session Tracking
    session_started = models.DateTimeField(blank=True, null=True)
    session_ended = models.DateTimeField(blank=True, null=True)
    actual_duration = models.IntegerField(default=0, help_text="Actual duration in minutes")
    
    # Payment Information
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHODS, default='wallet')
    payment_status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('refunded', 'Refunded'),
        ('failed', 'Failed'),
    ], default='paid')
    
    # Status and Notes
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    notes = models.TextField(blank=True, null=True)
    feedback = models.TextField(blank=True, null=True)
    rating = models.IntegerField(blank=True, null=True, help_text="User rating 1-5")
    
    # Analytics
    reminder_sent = models.BooleanField(default=False)
    follow_up_sent = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-scheduled_date']
    
    def __str__(self):
        return f"{self.user.username} - {self.title} - {self.scheduled_date}"
    
    @property
    def is_upcoming(self):
        return self.status == 'scheduled' and self.scheduled_date > timezone.now()
    
    @property
    def is_past_due(self):
        return self.status == 'scheduled' and self.scheduled_date < timezone.now()
    
    @property
    def is_active(self):
        return self.status == 'in_progress'
    
    @property
    def time_until_session(self):
        """Returns timedelta until session starts"""
        if self.status == 'scheduled':
            return self.scheduled_date - timezone.now()
        return None
    
    @property
    def can_join_meeting(self):
        """Check if user can join the meeting"""
        if not self.meeting_link:
            return False
        
        # Allow joining 10 minutes before scheduled time and up to 30 minutes after scheduled end time
        join_start = self.scheduled_date - timedelta(minutes=10)
        join_end = self.scheduled_date + timedelta(minutes=self.duration_minutes + 30)
        
        return join_start <= timezone.now() <= join_end and self.status in ['scheduled', 'in_progress']
    
    @property
    def meeting_status(self):
        """Get meeting status for display"""
        if self.status == 'completed':
            return 'Completed'
        elif self.status == 'in_progress':
            return 'Live Now'
        elif self.status == 'cancelled':
            return 'Cancelled'
        elif self.is_upcoming:
            if self.time_until_session and self.time_until_session.days > 0:
                return f"In {self.time_until_session.days} days"
            elif self.time_until_session and self.time_until_session.seconds > 3600:
                hours = self.time_until_session.seconds // 3600
                return f"In {hours} hours"
            elif self.time_until_session:
                minutes = max(0, self.time_until_session.seconds // 60)
                return f"In {minutes} minutes"
            else:
                return 'Starting Soon'
        else:
            return self.get_status_display()
    
    def generate_meeting_details(self):
        """Generate meeting details for video consultation with enhanced error handling"""
        if not self.meeting_id:
            try:
                # Generate unique meeting ID
                self.meeting_id = f"CONS{self.id:06d}{random.randint(1000, 9999)}"
                
                # Generate secure password
                self.meeting_password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
                
                # Generate meeting link based on platform
                if self.meeting_platform == 'jitsi':
                    self.meeting_link = f"https://meet.jit.si/ConsApp{self.meeting_id}"
                    self.join_url = self.meeting_link
                elif self.meeting_platform == 'zoom':
                    # This would integrate with Zoom API in a real implementation
                    self.meeting_link = f"https://zoom.us/j/{self.meeting_id}"
                    self.join_url = self.meeting_link
                elif self.meeting_platform == 'google_meet':
                    # Google Meet links are generated differently
                    self.meeting_link = f"https://meet.google.com/{self.meeting_id}"
                    self.join_url = self.meeting_link
                elif self.meeting_platform == 'teams':
                    self.meeting_link = f"https://teams.microsoft.com/l/meetup-join/{self.meeting_id}"
                    self.join_url = self.meeting_link
                else:  # custom
                    self.meeting_link = f"https://your-platform.com/meet/{self.meeting_id}"
                    self.join_url = self.meeting_link
                
                self.save()
                logger.info(f"Successfully generated meeting details for consultation {self.id}: {self.meeting_platform}")
                
            except Exception as e:
                logger.error(f"Error generating meeting details for consultation {self.id}: {str(e)}")
                # Set default Jitsi link as fallback
                try:
                    self.meeting_platform = 'jitsi'
                    self.meeting_id = f"CONS{self.id:06d}{random.randint(1000, 9999)}"
                    self.meeting_link = f"https://meet.jit.si/ConsApp{self.meeting_id}"
                    self.join_url = self.meeting_link
                    self.save()
                    logger.info(f"Fallback meeting details generated for consultation {self.id}")
                except Exception as fallback_error:
                    logger.error(f"Fallback meeting generation also failed for consultation {self.id}: {str(fallback_error)}")
    
    def start_session(self):
        """Mark session as started"""
        if self.status == 'scheduled':
            self.status = 'in_progress'
            self.session_started = timezone.now()
            self.save()
            logger.info(f"Consultation session started: {self.id}")
    
    def end_session(self):
        """Mark session as completed and calculate duration"""
        if self.status == 'in_progress' and self.session_started:
            self.status = 'completed'
            self.session_ended = timezone.now()
            
            # Calculate actual duration
            duration = self.session_ended - self.session_started
            self.actual_duration = int(duration.total_seconds() / 60)
            self.save()
            logger.info(f"Consultation session ended: {self.id}, duration: {self.actual_duration} minutes")
    
    def cancel_consultation(self, refund=False):
        """Cancel consultation with optional refund"""
        previous_status = self.status
        self.status = 'cancelled'
        
        if refund and self.payment_status == 'paid':
            try:
                # Process refund logic here
                self.payment_status = 'refunded'
                
                # Refund to user's wallet if paid with wallet
                if self.payment_method == 'wallet':
                    user_wallet = UserWallet.objects.get(user=self.user)
                    user_wallet.balance += self.price
                    user_wallet.save()
                    
                    # Create refund transaction
                    Transaction.objects.create(
                        user=self.user,
                        amount=self.price,
                        transaction_type='refund',
                        payment_method='wallet',
                        status='completed',
                        description=f"Refund for cancelled consultation: {self.title}",
                        consultation=self
                    )
                    logger.info(f"Refund processed for cancelled consultation {self.id}: ${self.price}")
            except Exception as e:
                logger.error(f"Error processing refund for consultation {self.id}: {str(e)}")
        
        self.save()
        logger.info(f"Consultation cancelled: {self.id}, previous status: {previous_status}, refund: {refund}")
    
    def get_level_display(self):
        return dict(self.LEVEL_CHOICES).get(self.level, self.level)
    
    def get_meeting_platform_display(self):
        return dict(self.MEETING_PLATFORMS).get(self.meeting_platform, self.meeting_platform)
    
    def get_preparation_checklist(self):
        """Return preparation checklist items"""
        return [
            "Test your audio and video equipment",
            "Prepare your portfolio details",
            "List your specific questions and goals",
            "Review recent market trends",
            "Have stable internet connection"
        ]
    
    @property
    def is_joinable(self):
        """Check if consultation can be joined now"""
        return self.can_join_meeting and self.meeting_link is not None


class ConsultationAttachment(models.Model):
    """Files attached to consultations (notes, resources, etc.)"""
    consultation = models.ForeignKey(Consultation, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='consultation_attachments/%Y/%m/%d/')
    file_name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=50)
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    description = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.file_name} - {self.consultation.title}"
    
    @property
    def file_size(self):
        """Get file size in human readable format"""
        try:
            if self.file:
                size = self.file.size
                if size < 1024:
                    return f"{size} B"
                elif size < 1024 * 1024:
                    return f"{size / 1024:.1f} KB"
                else:
                    return f"{size / (1024 * 1024):.1f} MB"
        except:
            pass
        return "Unknown"


class ConsultationReminder(models.Model):
    """Track consultation reminders"""
    consultation = models.ForeignKey(Consultation, on_delete=models.CASCADE)
    reminder_type = models.CharField(max_length=20, choices=[
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('push', 'Push Notification'),
    ])
    scheduled_time = models.DateTimeField()
    sent_time = models.DateTimeField(blank=True, null=True)
    is_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['scheduled_time']
    
    def __str__(self):
        return f"{self.reminder_type} reminder for {self.consultation.title}"
    
    def mark_as_sent(self):
        """Mark reminder as sent"""
        self.is_sent = True
        self.sent_time = timezone.now()
        self.save()


class ConsultationChatRoom(models.Model):
    """Chat room for consultation sessions"""
    consultation = models.OneToOneField(Consultation, on_delete=models.CASCADE, related_name='chat_room')
    room_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Chat Room - {self.consultation.title}"
    
    @property
    def message_count(self):
        """Get total number of messages in chat room"""
        return self.messages.count()
    
    @property
    def unread_count(self, user):
        """Get unread message count for specific user"""
        return self.messages.filter(is_read=False).exclude(user=user).count()


class ChatMessage(models.Model):
    """Individual chat messages"""
    MESSAGE_TYPES = [
        ('text', 'Text'),
        ('file', 'File'),
        ('system', 'System Message'),
    ]
    
    chat_room = models.ForeignKey(ConsultationChatRoom, on_delete=models.CASCADE, related_name='messages')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPES, default='text')
    content = models.TextField()
    file = models.FileField(upload_to='chat_files/%Y/%m/%d/', blank=True, null=True)
    file_name = models.CharField(max_length=255, blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['timestamp']
    
    def __str__(self):
        return f"{self.user.username}: {self.content[:50]}"
    
    def mark_as_read(self):
        """Mark message as read"""
        self.is_read = True
        self.save()
    
    @property
    def is_system_message(self):
        return self.message_type == 'system'


class ConsultationParticipant(models.Model):
    """Track participants in consultation chat rooms"""
    chat_room = models.ForeignKey(ConsultationChatRoom, on_delete=models.CASCADE, related_name='participants')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    joined_at = models.DateTimeField(auto_now_add=True)
    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['chat_room', 'user']
    
    def __str__(self):
        return f"{self.user.username} in {self.chat_room}"
    
    def update_online_status(self, is_online=True):
        """Update participant online status"""
        self.is_online = is_online
        self.last_seen = timezone.now()
        self.save()


class SiteSetting(models.Model):
    name = models.CharField(max_length=100)
    hero_video = models.FileField(upload_to='videos/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
    
    @classmethod
    def get_active_setting(cls):
        """Get the active site setting"""
        return cls.objects.filter(is_active=True).first()


class MpesaTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('deposit', 'Deposit'),
        ('withdrawal', 'Withdrawal'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('successful', 'Successful'),
        ('failed', 'Failed'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    phone_number = models.CharField(max_length=15)
    checkout_request_id = models.CharField(max_length=100, blank=True, null=True)
    merchant_request_id = models.CharField(max_length=100, blank=True, null=True)
    result_code = models.IntegerField(blank=True, null=True)
    result_desc = models.TextField(blank=True, null=True)
    mpesa_receipt_number = models.CharField(max_length=50, blank=True, null=True)
    transaction_date = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    def __str__(self):
        return f"{self.transaction_type} - {self.amount} - {self.status}"
    
    @property
    def is_successful(self):
        return self.status == 'successful'
    
    def mark_as_successful(self, mpesa_receipt_number, transaction_date):
        """Mark transaction as successful"""
        self.status = 'successful'
        self.mpesa_receipt_number = mpesa_receipt_number
        self.transaction_date = transaction_date
        self.save()
    
    def mark_as_failed(self, result_code, result_desc):
        """Mark transaction as failed"""
        self.status = 'failed'
        self.result_code = result_code
        self.result_desc = result_desc
        self.save()


# Signal handlers
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)
        UserWallet.objects.get_or_create(user=instance)
        logger.info(f"Created user profile and wallet for {instance.username}")

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    try:
        instance.userprofile.save()
    except UserProfile.DoesNotExist:
        UserProfile.objects.create(user=instance)
        logger.info(f"Created missing user profile for {instance.username}")
    try:
        instance.userwallet.save()
    except UserWallet.DoesNotExist:
        UserWallet.objects.create(user=instance)
        logger.info(f"Created missing user wallet for {instance.username}")

@receiver(post_save, sender=Consultation)
def generate_meeting_on_creation(sender, instance, created, **kwargs):
    """Automatically generate meeting details when consultation is created"""
    if created and instance.status == 'scheduled':
        instance.generate_meeting_details()
        logger.info(f"Generated meeting details for new consultation {instance.id}")

@receiver(post_save, sender=Consultation)
def create_consultation_reminders(sender, instance, created, **kwargs):
    """Create automatic reminders for consultations"""
    if created and instance.status == 'scheduled':
        try:
            # Create 24-hour reminder
            ConsultationReminder.objects.create(
                consultation=instance,
                reminder_type='email',
                scheduled_time=instance.scheduled_date - timedelta(hours=24)
            )
            
            # Create 1-hour reminder
            ConsultationReminder.objects.create(
                consultation=instance,
                reminder_type='email',
                scheduled_time=instance.scheduled_date - timedelta(hours=1)
            )
            logger.info(f"Created reminders for consultation {instance.id}")
        except Exception as e:
            logger.error(f"Error creating reminders for consultation {instance.id}: {str(e)}")

@receiver(post_save, sender=Consultation)
def create_consultation_chat_room(sender, instance, created, **kwargs):
    """Automatically create chat room when consultation is created"""
    if created and instance.status == 'scheduled':
        try:
            chat_room, created = ConsultationChatRoom.objects.get_or_create(consultation=instance)
            # Add user as participant
            ConsultationParticipant.objects.get_or_create(chat_room=chat_room, user=instance.user)
            logger.info(f"Created chat room for consultation {instance.id}")
        except Exception as e:
            logger.error(f"Error creating chat room for consultation {instance.id}: {str(e)}")

@receiver(post_save, sender=PurchasedAnalysis)
def update_analysis_sales_count(sender, instance, created, **kwargs):
    """Update analysis sales count when purchase is created"""
    if created:
        try:
            instance.analysis.sales_count = PurchasedAnalysis.objects.filter(analysis=instance.analysis).count()
            instance.analysis.save()
            logger.info(f"Updated sales count for analysis {instance.analysis.id}")
        except Exception as e:
            logger.error(f"Error updating sales count for analysis {instance.analysis.id}: {str(e)}")

@receiver(post_save, sender=AnalysisRating)
def update_analysis_rating(sender, instance, created, **kwargs):
    """Update analysis average rating when new rating is added"""
    if created:
        try:
            from django.db.models import Avg
            result = AnalysisRating.objects.filter(analysis=instance.analysis).aggregate(avg_rating=Avg('rating'))
            instance.analysis.rating = result['avg_rating'] or Decimal('0.00')
            instance.analysis.save()
            logger.info(f"Updated rating for analysis {instance.analysis.id}")
        except Exception as e:
            logger.error(f"Error updating rating for analysis {instance.analysis.id}: {str(e)}")