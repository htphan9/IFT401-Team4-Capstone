// market.js — handles the Buy/Sell trade modal on the market page
// Run once the page has fully loaded
document.addEventListener('DOMContentLoaded', function () {

    // Attach a click listener to every Buy and Sell button
    document.querySelectorAll('.trade-btn').forEach(function (button) {
        button.addEventListener('click', function () {

            // Read the stock info stored in the button's data attributes
            const action  = this.dataset.action;                        // "buy" or "sell"
            const stockId = this.dataset.stockId;                       // stock.id from the DB
            const ticker  = this.dataset.ticker;                        
            const price   = parseFloat(this.dataset.price).toFixed(2); 

            // Update the modal title to "Buy AAPL" or "Sell AAPL"
            document.getElementById('tradeModalLabel').textContent =
                (action === 'buy' ? 'Buy ' : 'Sell ') + ticker;

            // Pass the stock id and action into the hidden form fields so the backend knows what to do when the form is submitted
            document.getElementById('modal-stock-id').value = stockId;
            document.getElementById('modal-action').value   = action;

            // Show the current price inside the modal
            document.getElementById('modal-price-display').textContent =
                'Current Price: $' + price + ' per share';

            const submitBtn = document.getElementById('modal-submit-btn');
            submitBtn.textContent = action === 'buy' ? 'Confirm Buy' : 'Confirm Sell';
            submitBtn.className   = action === 'buy'
                ? 'btn btn-green-sm w-100'
                : 'btn btn-red-sm w-100';
        });
    });

    // Poll the server for updated stock prices every 1 minute
    function fetchPrices() {
        fetch('/api/prices')
            .then(function (response) {
                return response.json();
            })
            .then(function (data) {
                // Loop through each stock in the response
                for (var stockId in data) {
                    var stock = data[stockId];
                    var priceStr = '$' + stock.price.toFixed(2);

                    // Update price cell (works on both market and portfolio pages)
                    var priceCell = document.getElementById('price-' + stockId);
                    if (priceCell) {
                        priceCell.textContent = priceStr;
                    }

                    // Update daily high cell (market page)
                    var highCell = document.getElementById('high-' + stockId);
                    if (highCell) {
                        highCell.textContent = stock.high ? '$' + stock.high.toFixed(2) : '-';
                    }

                    // Update daily low cell (market page)
                    var lowCell = document.getElementById('low-' + stockId);
                    if (lowCell) {
                        lowCell.textContent = stock.low ? '$' + stock.low.toFixed(2) : '-';
                    }

                    // Update available shares cell (market page)
                    var availCell = document.getElementById('available-' + stockId);
                    if (availCell) {
                        availCell.textContent = stock.available.toLocaleString();
                    }

                    // Update data-price on Buy/Sell buttons so the modal shows the latest price
                    var buyBtn = document.getElementById('buy-btn-' + stockId);
                    if (buyBtn) {
                        buyBtn.dataset.price = stock.price;
                    }
                    var sellBtn = document.getElementById('sell-btn-' + stockId);
                    if (sellBtn) {
                        sellBtn.dataset.price = stock.price;
                    }

                    // Recalculate total value and unrealized P&L (portfolio page)
                    var valueCell = document.getElementById('value-' + stockId);
                    var pnlCell = document.getElementById('pnl-' + stockId);
                    if (valueCell && pnlCell) {
                        var row = pnlCell.closest('tr');
                        var shares = parseFloat(row.dataset.shares);
                        var avgCost = parseFloat(row.dataset.avgCost);

                        var totalValue = stock.price * shares;
                        var totalCost = avgCost * shares;
                        var pnl = totalValue - totalCost;

                        valueCell.textContent = '$' + totalValue.toFixed(2);

                        // Update P&L text and color
                        if (pnl >= 0) {
                            pnlCell.textContent = '+$' + pnl.toFixed(2);
                            pnlCell.className = 'text-success';
                        } else {
                            pnlCell.textContent = '-$' + Math.abs(pnl).toFixed(2);
                            pnlCell.className = 'text-danger';
                        }
                    }
                }
            });
    }

    // Fetch prices right away on page load, then every 1 minute
    fetchPrices();
    setInterval(fetchPrices, 60000); //60000 for 1 minute

});