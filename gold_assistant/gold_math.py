"""
gold_math.py - Motor de Cálculo Cuantitativo para XAUUSD en Cuentas FundingPips $10K
"""

class FundingPipsGoldCalculator:
    def __init__(self, account_size=10000.0, risk_pct=0.5):
        """
        account_size: Tamaño de cuenta en USD ($10,000)
        risk_pct: Porcentaje máximo de riesgo por operación (0.25% - 0.50% recomendado)
        """
        self.account_size = account_size
        self.risk_pct = risk_pct
        self.max_daily_loss_pct = 5.0 # Regla estándar FundingPips
        self.max_total_loss_pct = 10.0 # Regla estándar estática
        self.max_risk_amount = self.account_size * (self.risk_pct / 100.0)

    def calculate_lot_size(self, entry_price: float, stop_loss: float, contract_size: int = 100):
        """
        Calcula el lotaje exacto para no arriesgar más del porcentaje configurado.
        En XAUUSD: 1 lote estándar = 100 onzas troy.
        $1.00 de movimiento en el precio = $100 de ganancia/pérdida por cada 1.0 lote.
        1 pip en oro tradicionalmente = $0.10 de movimiento ($10 por lote).
        """
        price_risk = abs(entry_price - stop_loss)
        if price_risk <= 0:
            raise ValueError("El Stop Loss no puede ser igual al precio de entrada.")
        
        # Pérdida en USD por 1.0 lote = price_risk * contract_size
        risk_per_standard_lot = price_risk * contract_size
        
        # Lotaje teórico
        lot_size = self.max_risk_amount / risk_per_standard_lot
        # Redondear a 2 decimales (estándar MT5 / FundingPips)
        lot_size_rounded = round(lot_size, 2)
        
        # Validación de límites FundingPips ($10K no tiene límite estricto de 10 lotes, pero sí apalancamiento dinámico)
        # Apalancamiento dinámico en Master:
        # Hasta 0.05 lotes: 1:50
        # Hasta 0.10 lotes: 1:30
        # Hasta 0.15 lotes: 1:25
        # Hasta 0.25 lotes: 1:20
        # Hasta 0.50 lotes: 1:10
        # >0.50 lotes: 1:5
        
        margin_req = self.calculate_dynamic_margin(lot_size_rounded, entry_price)
        
        return {
            "account_size": self.account_size,
            "risk_percentage": f"{self.risk_pct}%",
            "risk_usd": self.max_risk_amount,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "price_delta": round(price_risk, 2),
            "lot_size": lot_size_rounded,
            "estimated_margin_usd": round(margin_req, 2),
            "split_positions": {
                "order_1_lots": round(lot_size_rounded / 2.0, 2),
                "order_2_lots": round(lot_size_rounded - round(lot_size_rounded / 2.0, 2), 2),
                "tp1_ratio": "1:1.5 (Cierre de Orden 1 + Mover Orden 2 a Breakeven)",
                "tp2_ratio": "1:3+ (Runner hacia liquidez mayor)"
            }
        }

    def calculate_dynamic_margin(self, lots: float, price: float):
        """
        Apalancamiento dinámico escalonado de FundingPips para metales (XAUUSD).
        """
        contract_size = 100
        rem_lots = lots
        margin = 0.0
        
        tiers = [
            (0.05, 50),
            (0.05, 30), # 0.05 a 0.10
            (0.05, 25), # 0.10 a 0.15
            (0.10, 20), # 0.15 a 0.25
            (0.25, 10), # 0.25 a 0.50
            (999.0, 5)  # > 0.50
        ]
        
        for tier_volume, leverage in tiers:
            if rem_lots <= 0:
                break
            v = min(rem_lots, tier_volume)
            tier_notional = v * contract_size * price
            margin += tier_notional / leverage
            rem_lots -= v
            
        return margin

if __name__ == '__main__':
    calc = FundingPipsGoldCalculator(account_size=10000.0, risk_pct=0.5)
    # Ejemplo: Entrada en Oro en $2740.00 con Stop Loss en $2734.00 ($6.00 de riesgo)
    res = calc.calculate_lot_size(entry_price=2740.0, stop_loss=2734.0)
    import json
    print(json.dumps(res, indent=2))
