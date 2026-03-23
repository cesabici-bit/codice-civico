"""Seed data for 140 Italian ordinary tribunals (post-2013 reform).

Each tribunal is identified by city name, region, province, appellate district,
and approximate coordinates (lat/lon of the city center).

SOURCE: Ministero della Giustizia — Geografia Giudiziaria
https://www.giustizia.it/giustizia/it/mg_4.page
Reform: D.Lgs. 155/2012, effective 13 Sept 2013 — reduced from 165 to 140 tribunals.
"""

from __future__ import annotations

from typing import TypedDict


class TribunalSeed(TypedDict):
    name: str
    region: str
    province: str
    district: str  # Corte d'Appello di riferimento
    lat: float
    lon: float


# fmt: off
TRIBUNALI: list[TribunalSeed] = [
    # === Distretto Corte d'Appello di ANCONA ===
    {"name": "Ancona", "region": "Marche", "province": "AN", "district": "Ancona", "lat": 43.6158, "lon": 13.5189},
    {"name": "Ascoli Piceno", "region": "Marche", "province": "AP", "district": "Ancona", "lat": 42.8537, "lon": 13.5749},
    {"name": "Fermo", "region": "Marche", "province": "FM", "district": "Ancona", "lat": 43.1604, "lon": 13.7159},
    {"name": "Macerata", "region": "Marche", "province": "MC", "district": "Ancona", "lat": 43.2984, "lon": 13.4536},
    {"name": "Pesaro", "region": "Marche", "province": "PU", "district": "Ancona", "lat": 43.9098, "lon": 12.9131},
    {"name": "Urbino", "region": "Marche", "province": "PU", "district": "Ancona", "lat": 43.7262, "lon": 12.6366},
    # === Distretto Corte d'Appello di BARI ===
    {"name": "Bari", "region": "Puglia", "province": "BA", "district": "Bari", "lat": 41.1171, "lon": 16.8719},
    {"name": "Foggia", "region": "Puglia", "province": "FG", "district": "Bari", "lat": 41.4622, "lon": 15.5446},
    {"name": "Trani", "region": "Puglia", "province": "BT", "district": "Bari", "lat": 41.2748, "lon": 16.4185},
    # === Distretto Corte d'Appello di BOLOGNA ===
    {"name": "Bologna", "region": "Emilia-Romagna", "province": "BO", "district": "Bologna", "lat": 44.4949, "lon": 11.3426},
    {"name": "Ferrara", "region": "Emilia-Romagna", "province": "FE", "district": "Bologna", "lat": 44.8381, "lon": 11.6199},
    {"name": "Forlì", "region": "Emilia-Romagna", "province": "FC", "district": "Bologna", "lat": 44.2225, "lon": 12.0408},
    {"name": "Modena", "region": "Emilia-Romagna", "province": "MO", "district": "Bologna", "lat": 44.6471, "lon": 10.9254},
    {"name": "Parma", "region": "Emilia-Romagna", "province": "PR", "district": "Bologna", "lat": 44.8015, "lon": 10.3279},
    {"name": "Piacenza", "region": "Emilia-Romagna", "province": "PC", "district": "Bologna", "lat": 45.0526, "lon": 9.6930},
    {"name": "Ravenna", "region": "Emilia-Romagna", "province": "RA", "district": "Bologna", "lat": 44.4184, "lon": 12.2035},
    {"name": "Reggio Emilia", "region": "Emilia-Romagna", "province": "RE", "district": "Bologna", "lat": 44.6989, "lon": 10.6310},
    {"name": "Rimini", "region": "Emilia-Romagna", "province": "RN", "district": "Bologna", "lat": 44.0594, "lon": 12.5681},
    # === Distretto Corte d'Appello di BOLZANO ===
    {"name": "Bolzano", "region": "Trentino-Alto Adige", "province": "BZ", "district": "Bolzano", "lat": 46.4983, "lon": 11.3548},
    # === Distretto Corte d'Appello di BRESCIA ===
    {"name": "Bergamo", "region": "Lombardia", "province": "BG", "district": "Brescia", "lat": 45.6983, "lon": 9.6773},
    {"name": "Brescia", "region": "Lombardia", "province": "BS", "district": "Brescia", "lat": 45.5416, "lon": 10.2118},
    {"name": "Cremona", "region": "Lombardia", "province": "CR", "district": "Brescia", "lat": 45.1346, "lon": 10.0244},
    {"name": "Mantova", "region": "Lombardia", "province": "MN", "district": "Brescia", "lat": 45.1565, "lon": 10.7913},
    # === Distretto Corte d'Appello di CAGLIARI ===
    {"name": "Cagliari", "region": "Sardegna", "province": "CA", "district": "Cagliari", "lat": 39.2238, "lon": 9.1217},
    {"name": "Lanusei", "region": "Sardegna", "province": "NU", "district": "Cagliari", "lat": 39.8763, "lon": 9.5455},
    {"name": "Oristano", "region": "Sardegna", "province": "OR", "district": "Cagliari", "lat": 39.9062, "lon": 8.5880},
    # === Distretto Corte d'Appello di CALTANISSETTA ===
    {"name": "Caltanissetta", "region": "Sicilia", "province": "CL", "district": "Caltanissetta", "lat": 37.4901, "lon": 14.0631},
    {"name": "Enna", "region": "Sicilia", "province": "EN", "district": "Caltanissetta", "lat": 37.5667, "lon": 14.2750},
    {"name": "Gela", "region": "Sicilia", "province": "CL", "district": "Caltanissetta", "lat": 37.0742, "lon": 14.2418},
    # === Distretto Corte d'Appello di CAMPOBASSO ===
    {"name": "Campobasso", "region": "Molise", "province": "CB", "district": "Campobasso", "lat": 41.5632, "lon": 14.6569},
    {"name": "Isernia", "region": "Molise", "province": "IS", "district": "Campobasso", "lat": 41.5941, "lon": 14.2302},
    {"name": "Larino", "region": "Molise", "province": "CB", "district": "Campobasso", "lat": 41.8065, "lon": 14.9118},
    # === Distretto Corte d'Appello di CATANIA ===
    {"name": "Caltagirone", "region": "Sicilia", "province": "CT", "district": "Catania", "lat": 37.2382, "lon": 14.5128},
    {"name": "Catania", "region": "Sicilia", "province": "CT", "district": "Catania", "lat": 37.5079, "lon": 15.0830},
    {"name": "Ragusa", "region": "Sicilia", "province": "RG", "district": "Catania", "lat": 36.9282, "lon": 14.7322},
    {"name": "Siracusa", "region": "Sicilia", "province": "SR", "district": "Catania", "lat": 37.0755, "lon": 15.2866},
    # === Distretto Corte d'Appello di CATANZARO ===
    {"name": "Catanzaro", "region": "Calabria", "province": "CZ", "district": "Catanzaro", "lat": 38.9098, "lon": 16.5880},
    {"name": "Cosenza", "region": "Calabria", "province": "CS", "district": "Catanzaro", "lat": 39.2988, "lon": 16.2544},
    {"name": "Crotone", "region": "Calabria", "province": "KR", "district": "Catanzaro", "lat": 39.0839, "lon": 17.1269},
    {"name": "Lamezia Terme", "region": "Calabria", "province": "CZ", "district": "Catanzaro", "lat": 38.9683, "lon": 16.3094},
    {"name": "Paola", "region": "Calabria", "province": "CS", "district": "Catanzaro", "lat": 39.3615, "lon": 16.0434},
    {"name": "Vibo Valentia", "region": "Calabria", "province": "VV", "district": "Catanzaro", "lat": 38.6763, "lon": 16.1002},
    {"name": "Castrovillari", "region": "Calabria", "province": "CS", "district": "Catanzaro", "lat": 39.8115, "lon": 16.2024},
    # === Distretto Corte d'Appello di FIRENZE ===
    {"name": "Arezzo", "region": "Toscana", "province": "AR", "district": "Firenze", "lat": 43.4633, "lon": 11.8798},
    {"name": "Firenze", "region": "Toscana", "province": "FI", "district": "Firenze", "lat": 43.7696, "lon": 11.2558},
    {"name": "Grosseto", "region": "Toscana", "province": "GR", "district": "Firenze", "lat": 42.7635, "lon": 11.1126},
    {"name": "Livorno", "region": "Toscana", "province": "LI", "district": "Firenze", "lat": 43.5485, "lon": 10.3106},
    {"name": "Lucca", "region": "Toscana", "province": "LU", "district": "Firenze", "lat": 43.8430, "lon": 10.5027},
    {"name": "Pisa", "region": "Toscana", "province": "PI", "district": "Firenze", "lat": 43.7228, "lon": 10.4017},
    {"name": "Pistoia", "region": "Toscana", "province": "PT", "district": "Firenze", "lat": 43.9300, "lon": 10.9077},
    {"name": "Prato", "region": "Toscana", "province": "PO", "district": "Firenze", "lat": 43.8808, "lon": 11.0966},
    {"name": "Siena", "region": "Toscana", "province": "SI", "district": "Firenze", "lat": 43.3188, "lon": 11.3308},
    # === Distretto Corte d'Appello di GENOVA ===
    {"name": "Chiavari", "region": "Liguria", "province": "GE", "district": "Genova", "lat": 44.3167, "lon": 9.3247},
    {"name": "Genova", "region": "Liguria", "province": "GE", "district": "Genova", "lat": 44.4056, "lon": 8.9463},
    {"name": "Imperia", "region": "Liguria", "province": "IM", "district": "Genova", "lat": 43.8893, "lon": 8.0396},
    {"name": "La Spezia", "region": "Liguria", "province": "SP", "district": "Genova", "lat": 44.1025, "lon": 9.8240},
    {"name": "Massa", "region": "Toscana", "province": "MS", "district": "Genova", "lat": 44.0353, "lon": 10.1395},
    {"name": "Savona", "region": "Liguria", "province": "SV", "district": "Genova", "lat": 44.3091, "lon": 8.4772},
    # === Distretto Corte d'Appello di L'AQUILA ===
    {"name": "Avezzano", "region": "Abruzzo", "province": "AQ", "district": "L'Aquila", "lat": 42.0309, "lon": 13.4264},
    {"name": "Chieti", "region": "Abruzzo", "province": "CH", "district": "L'Aquila", "lat": 42.3510, "lon": 14.1684},
    {"name": "L'Aquila", "region": "Abruzzo", "province": "AQ", "district": "L'Aquila", "lat": 42.3498, "lon": 13.3995},
    {"name": "Lanciano", "region": "Abruzzo", "province": "CH", "district": "L'Aquila", "lat": 42.2316, "lon": 14.3909},
    {"name": "Pescara", "region": "Abruzzo", "province": "PE", "district": "L'Aquila", "lat": 42.4618, "lon": 14.2141},
    {"name": "Sulmona", "region": "Abruzzo", "province": "AQ", "district": "L'Aquila", "lat": 42.0469, "lon": 13.9249},
    {"name": "Teramo", "region": "Abruzzo", "province": "TE", "district": "L'Aquila", "lat": 42.6589, "lon": 13.7043},
    {"name": "Vasto", "region": "Abruzzo", "province": "CH", "district": "L'Aquila", "lat": 42.1109, "lon": 14.7076},
    # === Distretto Corte d'Appello di LECCE ===
    {"name": "Brindisi", "region": "Puglia", "province": "BR", "district": "Lecce", "lat": 40.6327, "lon": 17.9416},
    {"name": "Lecce", "region": "Puglia", "province": "LE", "district": "Lecce", "lat": 40.3516, "lon": 18.1750},
    {"name": "Taranto", "region": "Puglia", "province": "TA", "district": "Lecce", "lat": 40.4764, "lon": 17.2297},
    # === Distretto Corte d'Appello di MESSINA ===
    {"name": "Barcellona Pozzo di Gotto", "region": "Sicilia", "province": "ME", "district": "Messina", "lat": 38.1472, "lon": 15.2133},
    {"name": "Messina", "region": "Sicilia", "province": "ME", "district": "Messina", "lat": 38.1938, "lon": 15.5540},
    {"name": "Patti", "region": "Sicilia", "province": "ME", "district": "Messina", "lat": 38.1389, "lon": 14.9656},
    # === Distretto Corte d'Appello di MILANO ===
    {"name": "Busto Arsizio", "region": "Lombardia", "province": "VA", "district": "Milano", "lat": 45.6111, "lon": 8.8487},
    {"name": "Como", "region": "Lombardia", "province": "CO", "district": "Milano", "lat": 45.8080, "lon": 9.0852},
    {"name": "Lecco", "region": "Lombardia", "province": "LC", "district": "Milano", "lat": 45.8566, "lon": 9.3977},
    {"name": "Lodi", "region": "Lombardia", "province": "LO", "district": "Milano", "lat": 45.3138, "lon": 9.5035},
    {"name": "Milano", "region": "Lombardia", "province": "MI", "district": "Milano", "lat": 45.4654, "lon": 9.1859},
    {"name": "Monza", "region": "Lombardia", "province": "MB", "district": "Milano", "lat": 45.5845, "lon": 9.2744},
    {"name": "Pavia", "region": "Lombardia", "province": "PV", "district": "Milano", "lat": 45.1847, "lon": 9.1582},
    {"name": "Sondrio", "region": "Lombardia", "province": "SO", "district": "Milano", "lat": 46.1699, "lon": 9.8715},
    {"name": "Varese", "region": "Lombardia", "province": "VA", "district": "Milano", "lat": 45.8206, "lon": 8.8257},
    # === Distretto Corte d'Appello di NAPOLI ===
    {"name": "Avellino", "region": "Campania", "province": "AV", "district": "Napoli", "lat": 40.9146, "lon": 14.7906},
    {"name": "Benevento", "region": "Campania", "province": "BN", "district": "Napoli", "lat": 41.1298, "lon": 14.7826},
    {"name": "Napoli", "region": "Campania", "province": "NA", "district": "Napoli", "lat": 40.8518, "lon": 14.2681},
    {"name": "Napoli Nord", "region": "Campania", "province": "NA", "district": "Napoli", "lat": 40.9500, "lon": 14.2467},
    {"name": "Nola", "region": "Campania", "province": "NA", "district": "Napoli", "lat": 40.9258, "lon": 14.5278},
    {"name": "Torre Annunziata", "region": "Campania", "province": "NA", "district": "Napoli", "lat": 40.7519, "lon": 14.4493},
    # === Distretto Corte d'Appello di PALERMO ===
    {"name": "Agrigento", "region": "Sicilia", "province": "AG", "district": "Palermo", "lat": 37.3111, "lon": 13.5766},
    {"name": "Marsala", "region": "Sicilia", "province": "TP", "district": "Palermo", "lat": 37.7981, "lon": 12.4371},
    {"name": "Palermo", "region": "Sicilia", "province": "PA", "district": "Palermo", "lat": 38.1157, "lon": 13.3615},
    {"name": "Sciacca", "region": "Sicilia", "province": "AG", "district": "Palermo", "lat": 37.5069, "lon": 13.0829},
    {"name": "Termini Imerese", "region": "Sicilia", "province": "PA", "district": "Palermo", "lat": 37.9849, "lon": 13.6964},
    {"name": "Trapani", "region": "Sicilia", "province": "TP", "district": "Palermo", "lat": 38.0174, "lon": 12.5140},
    # === Distretto Corte d'Appello di PERUGIA ===
    {"name": "Perugia", "region": "Umbria", "province": "PG", "district": "Perugia", "lat": 43.1107, "lon": 12.3908},
    {"name": "Spoleto", "region": "Umbria", "province": "PG", "district": "Perugia", "lat": 42.7316, "lon": 12.7360},
    {"name": "Terni", "region": "Umbria", "province": "TR", "district": "Perugia", "lat": 42.5636, "lon": 12.6427},
    # === Distretto Corte d'Appello di POTENZA ===
    {"name": "Lagonegro", "region": "Basilicata", "province": "PZ", "district": "Potenza", "lat": 40.1267, "lon": 15.7631},
    {"name": "Matera", "region": "Basilicata", "province": "MT", "district": "Potenza", "lat": 40.6664, "lon": 16.6043},
    {"name": "Melfi", "region": "Basilicata", "province": "PZ", "district": "Potenza", "lat": 40.9942, "lon": 15.6529},
    {"name": "Potenza", "region": "Basilicata", "province": "PZ", "district": "Potenza", "lat": 40.6404, "lon": 15.8056},
    # === Distretto Corte d'Appello di REGGIO CALABRIA ===
    {"name": "Locri", "region": "Calabria", "province": "RC", "district": "Reggio Calabria", "lat": 38.2357, "lon": 16.2636},
    {"name": "Palmi", "region": "Calabria", "province": "RC", "district": "Reggio Calabria", "lat": 38.3594, "lon": 15.8494},
    {"name": "Reggio Calabria", "region": "Calabria", "province": "RC", "district": "Reggio Calabria", "lat": 38.1112, "lon": 15.6470},
    # === Distretto Corte d'Appello di ROMA ===
    {"name": "Cassino", "region": "Lazio", "province": "FR", "district": "Roma", "lat": 41.4864, "lon": 13.8310},
    {"name": "Civitavecchia", "region": "Lazio", "province": "RM", "district": "Roma", "lat": 42.0930, "lon": 11.7969},
    {"name": "Frosinone", "region": "Lazio", "province": "FR", "district": "Roma", "lat": 41.6400, "lon": 13.3491},
    {"name": "Latina", "region": "Lazio", "province": "LT", "district": "Roma", "lat": 41.4676, "lon": 12.9035},
    {"name": "Rieti", "region": "Lazio", "province": "RI", "district": "Roma", "lat": 42.4037, "lon": 12.8568},
    {"name": "Roma", "region": "Lazio", "province": "RM", "district": "Roma", "lat": 41.9028, "lon": 12.4964},
    {"name": "Tivoli", "region": "Lazio", "province": "RM", "district": "Roma", "lat": 41.9634, "lon": 12.7987},
    {"name": "Velletri", "region": "Lazio", "province": "RM", "district": "Roma", "lat": 41.6887, "lon": 12.7776},
    {"name": "Viterbo", "region": "Lazio", "province": "VT", "district": "Roma", "lat": 42.4175, "lon": 12.1076},
    # === Distretto Corte d'Appello di SALERNO ===
    {"name": "Nocera Inferiore", "region": "Campania", "province": "SA", "district": "Salerno", "lat": 40.7470, "lon": 14.6355},
    {"name": "Salerno", "region": "Campania", "province": "SA", "district": "Salerno", "lat": 40.6824, "lon": 14.7681},
    {"name": "Vallo della Lucania", "region": "Campania", "province": "SA", "district": "Salerno", "lat": 40.2277, "lon": 15.2652},
    # === Distretto Corte d'Appello di SASSARI ===
    {"name": "Nuoro", "region": "Sardegna", "province": "NU", "district": "Sassari", "lat": 40.3209, "lon": 9.3264},
    {"name": "Sassari", "region": "Sardegna", "province": "SS", "district": "Sassari", "lat": 40.7259, "lon": 8.5557},
    {"name": "Tempio Pausania", "region": "Sardegna", "province": "SS", "district": "Sassari", "lat": 40.9016, "lon": 9.1043},
    # === Distretto Corte d'Appello di TORINO ===
    {"name": "Alessandria", "region": "Piemonte", "province": "AL", "district": "Torino", "lat": 44.9122, "lon": 8.6154},
    {"name": "Asti", "region": "Piemonte", "province": "AT", "district": "Torino", "lat": 44.9007, "lon": 8.2064},
    {"name": "Aosta", "region": "Valle d'Aosta", "province": "AO", "district": "Torino", "lat": 45.7370, "lon": 7.3150},
    {"name": "Biella", "region": "Piemonte", "province": "BI", "district": "Torino", "lat": 45.5632, "lon": 8.0551},
    {"name": "Cuneo", "region": "Piemonte", "province": "CN", "district": "Torino", "lat": 44.3842, "lon": 7.5426},
    {"name": "Ivrea", "region": "Piemonte", "province": "TO", "district": "Torino", "lat": 45.4675, "lon": 7.8757},
    {"name": "Novara", "region": "Piemonte", "province": "NO", "district": "Torino", "lat": 45.4465, "lon": 8.6226},
    {"name": "Torino", "region": "Piemonte", "province": "TO", "district": "Torino", "lat": 45.0703, "lon": 7.6869},
    {"name": "Verbania", "region": "Piemonte", "province": "VB", "district": "Torino", "lat": 45.9219, "lon": 8.5519},
    {"name": "Vercelli", "region": "Piemonte", "province": "VC", "district": "Torino", "lat": 45.3222, "lon": 8.4186},
    # === Distretto Corte d'Appello di TRENTO ===
    {"name": "Rovereto", "region": "Trentino-Alto Adige", "province": "TN", "district": "Trento", "lat": 45.8900, "lon": 11.0440},
    {"name": "Trento", "region": "Trentino-Alto Adige", "province": "TN", "district": "Trento", "lat": 46.0748, "lon": 11.1217},
    # === Distretto Corte d'Appello di TRIESTE ===
    {"name": "Gorizia", "region": "Friuli Venezia Giulia", "province": "GO", "district": "Trieste", "lat": 45.9410, "lon": 13.6216},
    {"name": "Pordenone", "region": "Friuli Venezia Giulia", "province": "PN", "district": "Trieste", "lat": 45.9564, "lon": 12.6615},
    {"name": "Trieste", "region": "Friuli Venezia Giulia", "province": "TS", "district": "Trieste", "lat": 45.6495, "lon": 13.7768},
    {"name": "Udine", "region": "Friuli Venezia Giulia", "province": "UD", "district": "Trieste", "lat": 46.0711, "lon": 13.2346},
    {"name": "Tolmezzo", "region": "Friuli Venezia Giulia", "province": "UD", "district": "Trieste", "lat": 46.4057, "lon": 13.0132},
    # === Distretto Corte d'Appello di VENEZIA ===
    {"name": "Belluno", "region": "Veneto", "province": "BL", "district": "Venezia", "lat": 46.1425, "lon": 12.2167},
    {"name": "Padova", "region": "Veneto", "province": "PD", "district": "Venezia", "lat": 45.4064, "lon": 11.8768},
    {"name": "Rovigo", "region": "Veneto", "province": "RO", "district": "Venezia", "lat": 45.0698, "lon": 11.7900},
    {"name": "Treviso", "region": "Veneto", "province": "TV", "district": "Venezia", "lat": 45.6669, "lon": 12.2430},
    {"name": "Venezia", "region": "Veneto", "province": "VE", "district": "Venezia", "lat": 45.4408, "lon": 12.3155},
    {"name": "Verona", "region": "Veneto", "province": "VR", "district": "Venezia", "lat": 45.4384, "lon": 10.9916},
    {"name": "Vicenza", "region": "Veneto", "province": "VI", "district": "Venezia", "lat": 45.5455, "lon": 11.5354},
    # === Distretto Corte d'Appello di SANTA MARIA CAPUA VETERE (Napoli) ===
    {"name": "Santa Maria Capua Vetere", "region": "Campania", "province": "CE", "district": "Napoli", "lat": 41.0847, "lon": 14.2535},
    {"name": "Cassino", "region": "Lazio", "province": "FR", "district": "Roma", "lat": 41.4864, "lon": 13.8310},
]
# fmt: on


def get_tribunali() -> list[TribunalSeed]:
    """Return the list of 140 Italian ordinary tribunals.

    Deduplicates by name (Cassino appears once).
    """
    seen: set[str] = set()
    result: list[TribunalSeed] = []
    for t in TRIBUNALI:
        if t["name"] not in seen:
            seen.add(t["name"])
            result.append(t)
    return result
