# MarGui-Project

> Questa repository contiene il progetto dell'esame di `Laboratorio di informatica applicata` del corso di `Ingegneria Informatica` presso l'`Università degli Studi di Pisa`, realizzato da `Samuele Guidetti` e `Alessio Marianelli`

## Contenuto
Il task che ci siamo fissati è quello di creare un classificatore binario per un determinato ticker azionario.
```bash
├── ARIMA.ipynb
├── ImprovedPipeline.ipynb
├── README.md
├── TickerTracker
│   ├── TickerTracker.py
│   ├── dockerfile
│   ├── indeces.py
│   ├── pip
│   │   └── requirements.txt
│   └── templates
│       └── index.html
├── TradingTestbentch.ipynb
├── data.py
├── documentation
│   ├── compile.sh
│   ├── documentation.md
│   └── documentation.pdf
├── stocks.txt
└── target.py
```

* `ARIMA.ipynb`: notebook che contiene la metodologia per convertire un insieme di modelli ARIMA in un classificatore binario rispettando il nostro target.  
* `ImprovedPipeline.ipynb`: notebook che continene tutti gli strumenti necessari per la parte di data analysis, traning e valutazione statistica del modello.
* `TickerTracker/`: Cartella contenente l'applicazione che sfrutta uno dei modelli sviluppati per monitorare i ticker azionari in tempo reale.
  * `TickerTracker.py`: script principale dell'applicazione web.
  * `dockerfile`: file per la creazione dell'immagine Docker dell'applicazione web.
  * `indeces.py`: script per la creazione di indici tecnici utilizzati come feature per il modello.
  * `pip/requirements.txt`: file contenente le dipendenze Python necessarie per l'applicazione web.
  * `templates/index.html`: file HTML per il rendering della pagina principale dell'applicazione web.
* `TradingTestbentch.ipynb`: notebook che permette di simulare una strategia di trading basata sulle predizioni del modello e la mette a confronto con strategie di trading basate su regole semplici.
* `data.py`: script per la gestione e la preparazione dei dati, che sfrutta alcune funzioni in `TickerTracker/indeces.py`.
* `documentation/`: cartella contenente la documentazione del progetto in formato markdown e PDF
* `stocks.txt`: file di testo contenente i ticker azionari di cui estrarre i dati con `data.py`.
* `target.py`: script per la definizione il target della classificazione binaria.