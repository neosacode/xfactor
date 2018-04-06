from dateutil.relativedelta import relativedelta
from django.utils import timezone

def generate_loan_table(charge, borrow_amount, times=24, raw_date=False):
	rows = {'data': []}
	months = charge.remaining_months

	if times > months:
		times = months

	for i in range(1, times + 1):
		payment_date = timezone.now() + relativedelta(months=i)
		total_amount = round(borrow_amount * (1 + charge.plan_grace_period.plan.loan_interest_percent / 100) ** i, 8)
		amount = round(total_amount / i, 8)

		if not raw_date:
			payment_date = payment_date.strftime('%d/%m/%Y')

		rows['data'].append(dict(
			times=i,
			payment_date=payment_date,
			interest_percent=round(charge.plan_grace_period.plan.loan_interest_percent, 2),
			total_amount=f'{total_amount:.8f}',
			amount=f'{amount:.8f}'
		))

	return rows


def generate_fixed_loan_table(charge, borrow_amount, times, raw_date=False):
	rows = {'data': []}
	months = charge.remaining_months

	if times > months:
		times = months

	for i in range(1, times + 1):
		payment_date = timezone.now() + relativedelta(months=i)
		total_amount = round(borrow_amount * (1 + charge.plan_grace_period.plan.loan_interest_percent / 100) ** times, 8)
		amount = round(total_amount / times, 8)

		if not raw_date:
			payment_date = payment_date.strftime('%d/%m/%Y')

		rows['data'].append(dict(
			times=i,
			payment_date=payment_date,
			interest_percent=round(charge.plan_grace_period.plan.loan_interest_percent, 2),
			total_amount=f'{total_amount:.8f}',
			amount=f'{amount:.8f}'
		))

	return rows