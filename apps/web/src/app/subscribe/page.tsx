'use client';

import { useState } from 'react';

const plans = [
  {
    id: 'basic',
    name: 'LeadGen Basic',
    price: 49,
    leads: 5,
    description: 'Perfect for small plumbing businesses',
    features: ['5 verified leads per month', 'Email delivery', 'Location matched leads', 'Reply YES to claim leads'],
    color: 'border-gray-600',
    badge: '',
  },
  {
    id: 'pro',
    name: 'LeadGen Pro',
    price: 99,
    leads: 20,
    description: 'For growing plumbing companies',
    features: ['20 verified leads per month', 'Priority support', 'Follow-up sequences', 'Reply YES to claim leads'],
    color: 'border-blue-500',
    badge: 'Most Popular',
  },
  {
    id: 'unlimited',
    name: 'LeadGen Pro Max',
    price: 199,
    leads: 50,
    description: 'For established commercial operations',
    features: ['50 verified leads per month', 'Dedicated support', 'Follow-up sequences', 'Voice call alerts', 'Reply YES to claim leads'],
    color: 'border-yellow-500',
    badge: 'Best Value',
  },
  {
    id: 'enterprise',
    name: 'LeadGen Enterprise',
    price: 349,
    leads: 100,
    description: 'For large commercial plumbing companies',
    features: ['100 verified leads per month', 'Dedicated account manager', 'Priority lead matching', 'Follow-up sequences', 'Voice call alerts', 'Custom reporting'],
    color: 'border-purple-500',
    badge: 'Enterprise',
  },
];

export default function SubscribePage() {
  const [loading, setLoading] = useState<string | null>(null);
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');

  async function handleSubscribe(planId: string) {
    if (!email) {
      setError('Please enter your email address');
      return;
    }
    setError('');
    setLoading(planId);

    try {
      const res = await fetch('/api/proxy/stripe/create-checkout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          plan: planId,
          plumber_email: email,
          plumber_id: 0,
        }),
      });

      const data = await res.json();

      if (data.checkout_url) {
        window.location.href = data.checkout_url;
      } else {
        setError('Failed to create checkout session. Please try again.');
      }
    } catch (e) {
      setError('Something went wrong. Please try again.');
    } finally {
      setLoading(null);
    }
  }

  return (
    <div className="min-h-screen bg-gray-950 text-white py-16 px-4">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold mb-4">Get Commercial Plumbing Leads</h1>
          <p className="text-gray-400 text-lg">Verified leads delivered directly to your inbox. Exclusively yours — never shared.</p>
          <p className="text-green-400 text-sm mt-2">Commercial leads from just £9.80 each — industry average is £25</p>
        </div>

        <div className="mb-8 max-w-md mx-auto">
          <label className="block text-sm text-gray-400 mb-2">Your email address</label>
          <input
            type="email"
            value={email}
            onChange={e => setEmail(e.target.value)}
            placeholder="you@yourcompany.com"
            className="w-full bg-gray-800 border border-gray-600 rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
          />
          {error && <p className="text-red-400 text-sm mt-2">{error}</p>}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {plans.map(plan => (
            <div key={plan.id} className={`bg-gray-900 border-2 ${plan.color} rounded-xl p-6 relative flex flex-col`}>
              {plan.badge && (
                <span className={`absolute -top-3 left-1/2 -translate-x-1/2 text-white text-xs font-bold px-3 py-1 rounded-full ${
                  plan.badge === 'Most Popular' ? 'bg-blue-500' :
                  plan.badge === 'Best Value' ? 'bg-yellow-500 text-gray-900' :
                  plan.badge === 'Enterprise' ? 'bg-purple-600' : 'bg-gray-600'
                }`}>
                  {plan.badge}
                </span>
              )}
              <h2 className="text-xl font-bold mb-1">{plan.name}</h2>
              <p className="text-gray-400 text-sm mb-4">{plan.description}</p>
              <div className="mb-2">
                <span className="text-4xl font-bold">£{plan.price}</span>
                <span className="text-gray-400">/month</span>
              </div>
              <p className="text-green-400 text-xs mb-6">£{(plan.price / plan.leads).toFixed(2)} per lead</p>
              <ul className="space-y-2 mb-8 flex-1">
                {plan.features.map((f, i) => (
                  <li key={i} className="flex items-center gap-2 text-sm text-gray-300">
                    <span className="text-green-400">✓</span> {f}
                  </li>
                ))}
              </ul>
              <button
                onClick={() => handleSubscribe(plan.id)}
                disabled={loading === plan.id}
                className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-semibold py-3 rounded-lg transition mt-auto"
              >
                {loading === plan.id ? 'Loading...' : 'Get Started'}
              </button>
            </div>
          ))}
        </div>

        <p className="text-center text-gray-500 text-sm mt-8">
          Cancel anytime. No contracts. Leads delivered within 24 hours of signup.
        </p>
      </div>
    </div>
  );
}