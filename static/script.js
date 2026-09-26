document.addEventListener("DOMContentLoaded", async function () {

    // 1. Load Waste Trends chart
    const canvas = document.getElementById("wasteChart");

    if (canvas) {
        try {
            const response = await fetch("/api/waste-data");

            if (!response.ok) {
                throw new Error("Could not load waste data");
            }

            const wasteData = await response.json();

            const labels = [
                "Food Waste",
                "Plastic",
                "Paper",
                "Metal",
                "E-Waste"
            ];

            const values = labels.map(type => wasteData[type] || 0);

            new Chart(canvas.getContext("2d"), {
                type: "bar",

                data: {
                    labels: labels,
                    datasets: [{
                        label: "Waste Collected (kg)",
                        data: values,
                        backgroundColor: [
                            "#ff6384",
                            "#36a2eb",
                            "#ffcd56",
                            "#4bc0c0",
                            "#9966ff"
                        ],
                        borderWidth: 1
                    }]
                },

                options: {
                    responsive: true,
                    scales: {
                        y: {
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: "Quantity (kg)"
                            }
                        }
                    }
                }
            });

        } catch (error) {
            console.error("Dashboard error:", error);
        }
    }


    // 2. Load Waste History and Total Waste
    const historyBody = document.getElementById("wasteHistory");
    const totalElement = document.getElementById("totalWaste");

    if (historyBody && totalElement) {
        try {
            const response = await fetch("/api/waste-history");

            if (!response.ok) {
                throw new Error("Unable to load history");
            }

            const records = await response.json();
            const recordCount = document.getElementById("recordCount");

            if (recordCount) {
                recordCount.textContent = records.length;
            }

            let total = 0;

            historyBody.innerHTML = "";

            if (records.length === 0) {
                historyBody.innerHTML =
                    "<tr><td colspan='3'>No waste records yet</td></tr>";
            }

            records.forEach(record => {
                total += Number(record.quantity);

                const row = document.createElement("tr");

                [
                    record.date,
                    record.waste_type,
                    Number(record.quantity).toFixed(1)
                ].forEach(value => {
                    const cell = document.createElement("td");
                    cell.textContent = value;
                    row.appendChild(cell);
                });

                historyBody.appendChild(row);
            });

            totalElement.textContent = total.toFixed(1);

        } catch (error) {
            console.error("History error:", error);

            totalElement.textContent = "Unavailable";

            historyBody.innerHTML =
                "<tr><td colspan='3'>Could not load waste history.</td></tr>";
        }
    }

});