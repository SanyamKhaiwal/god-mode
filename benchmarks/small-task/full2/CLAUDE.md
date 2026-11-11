## Learnings
- GST: seller state is UP (shop/tax.py SELLER_STATE); intra-state splits into cgst/sgst via round(tax/2,2), so cgst+sgst can be off by 0.01 from tax.
