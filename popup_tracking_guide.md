# Popup Tracking Implementation Guide

This guide explains how to implement popup tracking in the Shopify store to identify which popups are effective vs. causing user frustration.

## Overview

To track popup performance, we need to send custom events to PostHog when:
1. A popup is displayed
2. A user interacts with a popup (clicks, dismisses)
3. A popup leads to a conversion

## Required Events

### 1. `popup_shown` Event
Track when any popup is displayed to a user.

### 2. `popup_clicked` Event
Track when a user clicks on a popup (CTA button, link, etc.).

### 3. `popup_dismissed` Event
Track when a user closes/dismisses a popup.

## Implementation Methods

### Method 1: Shopify Theme Code 

Add this to the theme's `theme.liquid` file or create a custom snippet:

```javascript
<script>
  // Track popup displays and interactions
  (function() {
    // Wait for PostHog to be available
    function trackPopupEvent(eventName, popupName, popupType) {
      if (typeof posthog !== 'undefined') {
        posthog.capture(eventName, {
          popup_name: popupName,
          popup_type: popupType || 'unknown',
          popup_app: 'shopify_app', // or 'justuno', 'privy', 'klaviyo', etc.
          timestamp: new Date().toISOString()
        });
      }
    }

    // Monitor DOM for popup appearances
    const observer = new MutationObserver(function(mutations) {
      mutations.forEach(function(mutation) {
        mutation.addedNodes.forEach(function(node) {
          if (node.nodeType === 1) { // Element node
            // Check for common popup selectors
            const popupSelectors = [
              '[class*="popup"]',
              '[class*="modal"]',
              '[id*="popup"]',
              '[id*="modal"]',
              '[data-popup]',
              '.justuno-popup',
              '.privy-popup',
              '.klaviyo-popup',
              '.optinmonster-popup'
            ];

            popupSelectors.forEach(selector => {
              const popup = node.querySelector ? node.querySelector(selector) : null;
              if (popup || (node.matches && node.matches(selector))) {
                const popupElement = popup || node;
                const popupName = popupElement.getAttribute('data-popup-name') || 
                                 popupElement.id || 
                                 popupElement.className.split(' ')[0] || 
                                 'unknown';
                
                trackPopupEvent('popup_shown', popupName, 'auto-detected');
              }
            });
          }
        });
      });
    });

    // Start observing
    observer.observe(document.body, {
      childList: true,
      subtree: true
    });

    // Track popup dismissals (close buttons, overlays)
    document.addEventListener('click', function(e) {
      const target = e.target;
      if (target.matches('[class*="close"], [class*="dismiss"], [aria-label*="close" i]')) {
        const popup = target.closest('[class*="popup"], [class*="modal"]');
        if (popup) {
          const popupName = popup.getAttribute('data-popup-name') || 
                           popup.id || 
                           popup.className.split(' ')[0] || 
                           'unknown';
          trackPopupEvent('popup_dismissed', popupName);
        }
      }
    });

    // Track popup clicks (CTAs, links)
    document.addEventListener('click', function(e) {
      const target = e.target;
      const popup = target.closest('[class*="popup"], [class*="modal"]');
      if (popup && (target.matches('a, button, [role="button"]'))) {
        const popupName = popup.getAttribute('data-popup-name') || 
                         popup.id || 
                         popup.className.split(' ')[0] || 
                         'unknown';
        trackPopupEvent('popup_clicked', popupName);
      }
    });
  })();
</script>
```

### Method 2: App-Specific Tracking

#### For Justuno:
```javascript
// In Justuno settings or custom code
jQuery(document).on('justuno:popup:shown', function(e, popup) {
  if (typeof posthog !== 'undefined') {
    posthog.capture('popup_shown', {
      popup_name: popup.name || popup.id,
      popup_type: 'justuno',
      popup_campaign: popup.campaign || 'unknown'
    });
  }
});

jQuery(document).on('justuno:popup:clicked', function(e, popup) {
  if (typeof posthog !== 'undefined') {
    posthog.capture('popup_clicked', {
      popup_name: popup.name || popup.id,
      popup_type: 'justuno'
    });
  }
});
```

#### For Privy:
```javascript
// Privy provides callbacks
Privy('on', 'popup:shown', function(popup) {
  if (typeof posthog !== 'undefined') {
    posthog.capture('popup_shown', {
      popup_name: popup.name || popup.id,
      popup_type: 'privy',
      popup_campaign: popup.campaign || 'unknown'
    });
  }
});

Privy('on', 'popup:clicked', function(popup) {
  if (typeof posthog !== 'undefined') {
    posthog.capture('popup_clicked', {
      popup_name: popup.name || popup.id,
      popup_type: 'privy'
    });
  }
});
```

#### For Klaviyo:
```javascript
// Klaviyo popup tracking
_learnq.push(['onPopupShown', function(popup) {
  if (typeof posthog !== 'undefined') {
    posthog.capture('popup_shown', {
      popup_name: popup.name || popup.id,
      popup_type: 'klaviyo',
      popup_list: popup.list || 'unknown'
    });
  }
}]);

_learnq.push(['onPopupClicked', function(popup) {
  if (typeof posthog !== 'undefined') {
    posthog.capture('popup_clicked', {
      popup_name: popup.name || popup.id,
      popup_type: 'klaviyo'
    });
  }
}]);
```

### Method 3: Google Tag Manager (GTM)

If we want to use GTM, create triggers for:
- **Popup Display**: Custom event trigger for popup appearances
- **Popup Click**: Click trigger on popup CTAs
- **Popup Dismiss**: Click trigger on close buttons

Then send events to PostHog via GTM's Custom HTML tag.

## Event Properties

Each popup event should include these properties:

```javascript
{
  popup_name: "newsletter-signup",        // Unique identifier
  popup_type: "email-capture",            // Type: email-capture, discount, exit-intent, etc.
  popup_app: "justuno",                    // App name: justuno, privy, klaviyo, custom
  popup_campaign: "summer-sale-2024",     // Campaign name (optional)
  popup_position: "center",                // Position: center, bottom, top, sidebar
  popup_trigger: "exit-intent",           // Trigger: exit-intent, time-delay, scroll, etc.
  page_url: window.location.href,          // Page where popup appeared
  user_session: posthog.get_session_id()  // Session ID for correlation
}
```

## Advanced: Rage Click Correlation

To identify if popups are causing rage clicks, add this property when tracking rage clicks:

```javascript
// In your rage click tracking
posthog.capture('$rageclick', {
  popup_active: document.querySelector('[class*="popup"]') ? true : false,
  popup_name: getActivePopupName(), // Function to get current popup
  time_since_popup: getTimeSincePopup() // Seconds since popup appeared
});
```

## Testing

1. **Test in Browser Console:**
```javascript
// Manually trigger events to test
posthog.capture('popup_shown', {
  popup_name: 'test-popup',
  popup_type: 'test',
  popup_app: 'manual-test'
});
```

2. **Verify in PostHog:**
   - Go to PostHog → Events
   - Filter for `popup_shown`, `popup_clicked`, `popup_dismissed`
   - Check that events are being captured with correct properties

3. **Run Analytics Pipeline:**
```bash
python fetch_metrics.py
python run_report_generation.py
```

## Metrics We'll Get

Once tracking is implemented, the analytics pipeline will provide:

1. **Popup Performance Metrics** (`popup_metrics.csv`):
   - Total displays per popup
   - Click rates
   - Dismissal rates
   - Engagement rates

2. **Popup-Rage Correlation** (`popup_rage_correlation.csv`):
   - Correlation between popups and rage clicks
   - Which popups may be causing frustration

3. **AI Insights**:
   - Which popups are effective
   - Which popups should be removed
   - Recommendations for optimization

## Next Steps

1. Implement tracking code in your Shopify theme
2. Test that events are being captured
3. Run `python fetch_metrics.py` to collect data
4. Review the PDF report for insights
5. Remove or optimize popups based on data

## Troubleshooting

- Ensure event names match exactly: `popup_shown`, `popup_clicked`, `popup_dismissed`
- Check that `popup_name` property is being set
