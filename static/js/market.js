// market.js — handles the Buy/Sell trade modal on the market page
// Run once the page has fully loaded
document.addEventListener('DOMContentLoaded', function () {

    // Keep track of the current modal state so we can recalculate on the fly
    var modalState = {
        action: '',
        price: 0,
        owned: 0,
        avgCost: 0,
        balance: 0,
        ticker: '' // added for order summary -Donavan
    };

    // Grab references to modal elements
    var quantityInput = document.getElementById('modal-quantity');
    var submitBtn = document.getElementById('modal-submit-btn');
    var warningEl = document.getElementById('modal-warning');
    var ownedEl = document.getElementById('modal-owned');
    var maxBtn = document.getElementById('modal-max-btn');

    // Two-step confirm/cancel references -Donavan
    var step1 = document.getElementById('modal-step-1');
    var step2 = document.getElementById('modal-step-2');
    var reviewBtn = document.getElementById('modal-review-btn');
    var backBtn = document.getElementById('modal-back-btn');

    // Show step 1 (quantity entry), hide step 2 -Donavan
    function showStep1() {
        step1.classList.remove('d-none');
        step2.classList.add('d-none');
    }

    // Show step 2 (order summary), hide step 1 -Donavan
    function showStep2() {
        var quantity  = parseInt(quantityInput.value) || 0;
        var totalCost = quantity * modalState.price;
        var remaining = modalState.action === 'buy'
            ? modalState.balance - totalCost
            : modalState.balance + totalCost;

        document.getElementById('summary-action').textContent = modalState.action === 'buy' ? 'Buy' : 'Sell';
        document.getElementById('summary-ticker').textContent = modalState.ticker;
        document.getElementById('summary-shares').textContent = quantity.toLocaleString();
        document.getElementById('summary-price').textContent  = '$' + modalState.price.toFixed(2);
        document.getElementById('summary-total').textContent  = '$' + totalCost.toFixed(2);

        var remainingEl = document.getElementById('summary-remaining');
        remainingEl.textContent = '$' + remaining.toFixed(2);
        remainingEl.className   = remaining < 0 ? 'text-danger' : '';

        // Show P&L only when selling
        var pnlRow = document.getElementById('summary-pnl-row');
        if (modalState.action === 'sell') {
            pnlRow.classList.remove('d-none');
            var pnl   = (modalState.price - modalState.avgCost) * quantity;
            var pnlEl = document.getElementById('summary-pnl');
            pnlEl.textContent = (pnl >= 0 ? '+$' : '-$') + Math.abs(pnl).toFixed(2);
            pnlEl.className   = pnl >= 0 ? 'text-success' : 'text-danger';
        } else {
            pnlRow.classList.add('d-none');
        }

        step1.classList.add('d-none');
        step2.classList.remove('d-none');
    }

    // Validate quantity and show warnings -Donavan
    function validate() {
        var quantity  = parseInt(quantityInput.value) || 0;
        var totalCost = quantity * modalState.price;
        var hasError  = false;

        warningEl.classList.add('d-none');
        warningEl.textContent = '';

        if (modalState.action === 'buy' && totalCost > modalState.balance) {
            warningEl.textContent = 'Insufficient Funds';
            warningEl.classList.remove('d-none');
            hasError = true;
        }
        if (modalState.action === 'sell' && quantity > modalState.owned) {
            warningEl.textContent = 'Insufficient Shares Owned';
            warningEl.classList.remove('d-none');
            hasError = true;
        }

        reviewBtn.disabled = hasError || quantity < 1;
    }

    // Attach a click listener to every Buy and Sell button
    document.querySelectorAll('.trade-btn').forEach(function (button) {
        button.addEventListener('click', function () {

            // Read the stock info stored in the button's data attributes
            var action  = this.dataset.action;
            var stockId = this.dataset.stockId;
            var ticker  = this.dataset.ticker;
            var price   = parseFloat(this.dataset.price);
            var owned   = parseInt(this.dataset.owned) || 0;
            var avgCost = parseFloat(this.dataset.avgCost) || 0;

            // Read user balance from the page
            var balanceEl = document.getElementById('user-balance');
            var balance = parseFloat(balanceEl.dataset.balance) || 0;

            // Save state
            modalState.action  = action;
            modalState.price   = price;
            modalState.owned   = owned;
            modalState.avgCost = avgCost;
            modalState.balance = balance;
            modalState.ticker  = ticker; // -Donavan

            // Update the modal title to "Buy AAPL" or "Sell AAPL"
            document.getElementById('tradeModalLabel').textContent =
                (action === 'buy' ? 'Buy ' : 'Sell ') + ticker;

            // Pass the stock id and action into the hidden form fields
            document.getElementById('modal-stock-id').value = stockId;
            document.getElementById('modal-action').value   = action;

            // Show the current price inside the modal
            document.getElementById('modal-price-display').textContent =
                'Current Price: $' + price.toFixed(2) + ' per share';

            // Show shares owned
            ownedEl.textContent = owned.toLocaleString();

            // Style the submit button
            submitBtn.textContent = action === 'buy' ? 'Confirm Buy' : 'Confirm Sell';
            submitBtn.className   = action === 'buy'
                ? 'btn btn-green-sm w-50'
                : 'btn btn-red-sm w-50';

            // Reset and show step 1 -Donavan
            quantityInput.value = 1;
            showStep1();
            validate();
        });
    });

    // Recalculate when user changes the quantity
    quantityInput.addEventListener('input', function () {
        validate();
    });

    // Review button → advance to order summary -Donavan
    reviewBtn.addEventListener('click', function () {
        showStep2();
    });

    // Cancel button → back to quantity entry -Donavan
    backBtn.addEventListener('click', function () {
        showStep1();
    });

    // Reset modal to step 1 when closed -Donavan
    document.getElementById('tradeModal').addEventListener('hidden.bs.modal', function () {
        showStep1();
        quantityInput.value = 1;
        warningEl.classList.add('d-none');
    });

    // Max button — fill in the max quantity the user can buy or sell
    maxBtn.addEventListener('click', function () {
        if (modalState.action === 'buy') {
            var maxShares = Math.floor(modalState.balance / modalState.price);
            if (maxShares < 1) maxShares = 1;
            quantityInput.value = maxShares;
        } else {
            quantityInput.value = modalState.owned > 0 ? modalState.owned : 1;
        }
        validate();
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
                        buyBtn.dataset.available = stock.available;
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
