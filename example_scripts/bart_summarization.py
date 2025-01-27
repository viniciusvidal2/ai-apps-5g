from transformers import pipeline

summarizer = pipeline("summarization", model="facebook/bart-large-cnn")

ARTICLE = """ New York (CNN)When Liana Barrientos was 23 years old, she got married in Westchester County, New York.
A year later, she got married again in Westchester County, but to a different man and without divorcing her first husband.
Only 18 days after that marriage, she got hitched yet again. Then, Barrientos declared "I do" five more times, sometimes only within two weeks of each other.
In 2010, she married once more, this time in the Bronx. In an application for a marriage license, she stated it was her "first and only" marriage.
Barrientos, now 39, is facing two criminal counts of "offering a false instrument for filing in the first degree," referring to her false statements on the
2010 marriage license application, according to court documents.
Prosecutors said the marriages were part of an immigration scam.
On Friday, she pleaded not guilty at State Supreme Court in the Bronx, according to her attorney, Christopher Wright, who declined to comment further.
After leaving court, Barrientos was arrested and charged with theft of service and criminal trespass for allegedly sneaking into the New York subway through an emergency exit, said Detective
Annette Markowski, a police spokeswoman. In total, Barrientos has been married 10 times, with nine of her marriages occurring between 1999 and 2002.
All occurred either in Westchester County, Long Island, New Jersey or the Bronx. She is believed to still be married to four men, and at one time, she was married to eight men at once, prosecutors say.
Prosecutors said the immigration scam involved some of her husbands, who filed for permanent residence status shortly after the marriages.
Any divorces happened only after such filings were approved. It was unclear whether any of the men will be prosecuted.
The case was referred to the Bronx District Attorney\'s Office by Immigration and Customs Enforcement and the Department of Homeland Security\'s
Investigation Division. Seven of the men are from so-called "red-flagged" countries, including Egypt, Turkey, Georgia, Pakistan and Mali.
Her eighth husband, Rashid Rajput, was deported in 2006 to his native Pakistan after an investigation by the Joint Terrorism Task Force.
If convicted, Barrientos faces up to four years in prison.  Her next court appearance is scheduled for May 18.
"""
pergunta_sae = """
A Santo Antônio Energia S.A. é uma empresa de capital misto responsável pela construção e operação da Usina Hidrelétrica de Santo Antônio (UHS), localizada no Rio Madeira, na região do município de Porto Velho, em Rondônia. A UHS é um projeto emblemático no setor energético brasileiro, destacando-se por sua capacidade de geração renovável e impacto socioeconômico.
### Características Principais:
1. **Capacidade de Geração**:
   - A Usina Hidrelétrica de Santo Antônio tem uma capacidade instalada de cerca de 3,15 mil megawatts (MW), o que a coloca entre as maiores do Brasil e da América Latina.
2. **Inauguração e Operação**:
   - As obras começaram em 2008 e a usina foi oficialmente inaugurada em 2020. A operação comercial teve início no final de 2019, após anos de desenvolvimento intensivo.
3. **Construção e Engenharia**:
   - O projeto envolveu grandes avanços tecnológicos e logísticos, dadas as condições desafiadoras do local, que incluem um ambiente remoto e a necessidade de minimizar impactos ambientais.
4. **Parceria e Capitalização**:
   - A Santo Antônio Energia é uma joint venture formada por empresas nacionais e internacionais. Dentre os principais acionistas estão o Banco Nacional de Desenvolvimento Econômico e Social (BNDES), Furnas Centrais Elétricas, Elektro Participações e Serviços S.A., e a Jacto Participações e Empreendimentos Ltda.
5. **Impactos Socioeconômicos**:
   - A construção da usina gerou um significativo número de empregos durante o período das obras e também contribuiu para o desenvolvimento econômico regional.
   - Programas sociais foram implementados, visando melhorar a qualidade de vida nas comunidades locais.
6. **Impacto Ambiental**:
   - Apesar dos benefícios energéticos, houve preocupações ambientais relacionadas à biodiversidade e às populações ribeirinhas afetadas pela inundação do reservatório.
   - A empresa adotou medidas de mitigação ambiental, como programas de monitoramento e compensação para áreas impactadas.
7. **Inovação Tecnológica**:
   - A UHS é conhecida por seu sistema inovador de turbinas Kaplan, que permitem operar em um amplo intervalo de vazões, o que aumenta a eficiência energética e a flexibilidade operacional da usina. A Usina Hidrelétrica de Santo Antônio representa uma importante evolução na matriz energética brasileira, destacando-se pelo uso sustentável de recursos hídricos para produção de energia elétrica limpa. A empresa continua focada em operações responsáveis e na busca por soluções inovadoras que minimizem os impactos ambientais enquanto maximiza a eficiência energética.
"""
print(summarizer(pergunta_sae, max_length=300, min_length=30, do_sample=True))
