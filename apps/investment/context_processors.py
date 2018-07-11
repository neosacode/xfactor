from exchange_core.models import Accounts, Currencies, Statement


def accounts(request):
    if not request.user.is_authenticated:
        return {}

    checking_accounts = Accounts.objects.filter(user=request.user, currency__symbol='BTC', currency__type=Currencies.TYPES.checking)
    investment_accounts = Accounts.objects.filter(user=request.user, currency__symbol='BTC', currency__type=Currencies.TYPES.investment)
    checking_account = checking_accounts.first() if checking_accounts.exists() else None
    investment_account = investment_accounts.first() if investment_accounts.exists() else None

    return {
        'user_checking_account': checking_account,
        'user_investment_account': investment_account,
        'user_has_card': Statement.objects.filter(type__in=['course_subscription', 'advisor_card_request'], account__user=request.user).exists()
    }
