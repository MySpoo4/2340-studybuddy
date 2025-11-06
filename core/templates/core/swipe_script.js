function getTopCard() {
    return cards[cards.length - 1];
}

function removeTopCard(action) {
    if (cards.length === 0) return;

    const topCard = cards.pop();
    let rotation = (action === 'like' ? 15 : -15);
    topCard.style.transform = `translateX(${action === 'like' ? '200%' : '-200%'}) rotate(${rotation}deg)`;
    topCard.style.opacity = '0';

    setTimeout(() => {
        topCard.remove();
    }, 300);

    if (cards.length === 0) {
        // All cards have been swiped, so show the "no more profiles" card.
        noMoreProfilesCard.classList.remove('hidden');
    }
}

async function sendSwipeAction(liked) {
    const topCard = getTopCard();
    if (!topCard) return;

    const userId = topCard.dataset.userId;
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

    try {
        const response = await fetch("{% url 'core:swipe_action' %}", {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken,
            },
            body: JSON.stringify({ swiped_user_id: userId, liked: liked }),
        });

        if (!response.ok) throw new Error('Network response was not ok');

        const result = await response.json();

        if (result.status === 'match') {
            handleNewMatchPopup(result.popup_html); // Use the global handler from base.html
        }
    } catch (error) {
        console.error('Swipe action failed:', error);
        // Optionally, revert the card or show an error message
    }

    removeTopCard(liked ? 'like' : 'pass');
}

passBtn.addEventListener('click', () => sendSwipeAction(false));
likeBtn.addEventListener('click', () => sendSwipeAction(true));

// Keyboard navigation
document.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowLeft') {
        passBtn.click();
    } else if (e.key === 'ArrowRight') {
        likeBtn.click();
    }
});