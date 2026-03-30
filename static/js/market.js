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

});