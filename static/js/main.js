/**
 * VoiceOne Interactive Frontend Script
 * Handles real-time asynchronous voting, age calculation, and civic moderation feedback.
 */

document.addEventListener('DOMContentLoaded', () => {
    // 1. Live Age Calculator on Login Page
    const dobInput = document.getElementById('dob-input');
    const ageFeedback = document.getElementById('age-feedback');

    if (dobInput && ageFeedback) {
        dobInput.addEventListener('change', () => {
            const val = dobInput.value;
            if (!val) {
                ageFeedback.innerHTML = '';
                return;
            }
            const dob = new Date(val);
            const today = new Date();
            let age = today.getFullYear() - dob.getFullYear();
            const m = today.getMonth() - dob.getMonth();
            if (m < 0 || (m === 0 && today.getDate() < dob.getDate())) {
                age--;
            }

            if (isNaN(age)) {
                ageFeedback.innerHTML = '<span style="color: #C62828;">Invalid date</span>';
            } else if (age < 18) {
                ageFeedback.innerHTML = `<span style="color: #C62828; font-weight: 700;">⚠️ Age: ${age} years. (Minimum required age is 18).</span>`;
            } else {
                ageFeedback.innerHTML = `<span style="color: #2E7D32; font-weight: 700;">✅ Age: ${age} years. Eligible to participate.</span>`;
            }
        });
    }

    // 2. Interactive AJAX Vote Handling for Instant Latency-Free Updates
    const voteForms = document.querySelectorAll('.async-vote-form');
    voteForms.forEach(form => {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const pollId = form.getAttribute('data-poll-id');
            const submitBtn = e.submitter;
            const choice = submitBtn.value;

            try {
                const response = await fetch(`/polls/${pollId}/vote`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Accept': 'application/json'
                    },
                    body: JSON.stringify({ choice: choice })
                });

                const data = await response.json();
                if (data.success) {
                    // Update visual percentages
                    const forBar = document.getElementById(`bar-for-${pollId}`);
                    const againstBar = document.getElementById(`bar-against-${pollId}`);
                    const forPctText = document.getElementById(`pct-for-${pollId}`);
                    const againstPctText = document.getElementById(`pct-against-${pollId}`);
                    const totText = document.getElementById(`total-votes-${pollId}`);
                    const statusText = document.getElementById(`vote-status-${pollId}`);

                    if (forBar && againstBar) {
                        forBar.style.width = `${data.pct_for}%`;
                        againstBar.style.width = `${data.pct_against}%`;
                    }
                    if (forPctText && againstPctText) {
                        forPctText.textContent = `${data.pct_for}% (${data.votes_for} For)`;
                        againstPctText.textContent = `${data.pct_against}% (${data.votes_against} Against)`;
                    }
                    if (totText) {
                        totText.textContent = `${data.total_votes} Total Votes`;
                    }
                    if (statusText) {
                        statusText.innerHTML = `<span class="brand-badge" style="background:#2E7D32;">Voted ${data.choice}</span>`;
                    }

                    // Toggle active classes on buttons
                    const btnFor = form.querySelector('.btn-for');
                    const btnAgainst = form.querySelector('.btn-against');
                    if (btnFor && btnAgainst) {
                        if (choice === 'FOR') {
                            btnFor.classList.add('active');
                            btnAgainst.classList.remove('active');
                        } else {
                            btnAgainst.classList.add('active');
                            btnFor.classList.remove('active');
                        }
                    }
                } else {
                    alert(data.error || 'Vote could not be submitted.');
                }
            } catch (err) {
                // Fallback submit form normally
                form.submit();
            }
        });
    });

    // 3. Upvote Discussion Post AJAX
    const upvoteForms = document.querySelectorAll('.upvote-btn');
    upvoteForms.forEach(btn => {
        btn.addEventListener('click', async () => {
            const postId = btn.getAttribute('data-post-id');
            try {
                const response = await fetch(`/forum/${postId}/upvote`, {
                    method: 'POST',
                    headers: { 'Accept': 'application/json' }
                });
                const data = await response.json();
                if (data.success) {
                    btn.querySelector('.upvote-count').textContent = data.upvotes;
                    btn.classList.add('active');
                }
            } catch (err) {
                console.error(err);
            }
        });
    });
});
