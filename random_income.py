import random
from pprint import pprint

from decimal import Decimal


def decimal_split(amount, split_times=10, min_split_amount_percent=70, max_split_amount_percent=100):
	if not isinstance(split_times, int):
		raise Exception('Split times argument must be a integer')

	splited_amount = Decimal(amount) / split_times
	split_table = []
	loop_times = split_times

	start_random = splited_amount * Decimal(min_split_amount_percent / 100)
	end_random = splited_amount * Decimal(max_split_amount_percent / 100)

	for i in range(0, loop_times):
		split_table.append(Decimal(random.uniform(float(start_random), float(end_random))))

	increment_amount = (Decimal(amount) - sum(split_table)) / split_times
	return [increment_amount + n for n in split_table]


pprint(decimal_split(Decimal('3200'), 30))