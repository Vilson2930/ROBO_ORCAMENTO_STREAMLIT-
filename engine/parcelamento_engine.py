# ============================================================
# ROBO ORCAMENTO INTELIGENTE
# CELULA 1 - INSTALACAO PROFISSIONAL DAS BIBLIOTECAS
# ============================================================

print("=" * 80)
print("ROBO ORCAMENTO INTELIGENTE")
print("CELULA 1 - INSTALACAO DAS DEPENDENCIAS")
print("=" * 80)

!pip -q install pypdf pandas numpy openpyxl matplotlib reportlab

print("=" * 80)
print("DEPENDENCIAS INSTALADAS COM SUCESSO")
print("=" * 80)

print("""
Bibliotecas instaladas:

pypdf     -> leitura de faturas em PDF
pandas    -> organização dos dados em tabelas
numpy     -> cálculos financeiros
openpyxl  -> exportação para Excel
matplotlib-> gráficos financeiros
reportlab -> geração de relatório em PDF
""")

print("=" * 80)
print("AMBIENTE PRONTO PARA A CELULA 2")
print("=" * 80)
