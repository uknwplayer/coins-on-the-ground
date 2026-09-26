```javascript
const sellerChecks = () => {
  const checks = {
    initialCredit: {
      value: 'Ӿ10',
      conditions: [
        { name: 'unpaidRequest', status: 'pass' },
        { name: 'paidCompletion', status: 'pass' },
        { name: 'endpointReachability', status: 'pass' }
      ]
    },
    afterFourteenDays: {
      value: 'Ӿ15',
      days: 14,
      conditions: [
        { name: 'unpaidRequest', status: 'pass' },
        { name: 'paidCompletion', status: 'pass' },
        { name: 'endpointReachability', status: 'pass' }
      ]
    }
  };
  return checks;
};

const sellerEligibility = () => {
  const eligible = {
    seller: 'uknwplayer',
    status: 'newToNano',
    creditCount: 1,
    paymentMethod: 'publicRepository'
  };
  return eligible;
};
```