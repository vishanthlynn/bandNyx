const { validateEnquiry, enquiryMessage, deliverEnquiry } = require("../lib/booking/enquiry");

module.exports = async function handler(request, response) {
  if (request.method !== "POST") {
    response.setHeader("Allow", "POST");
    return response.status(405).json({ delivered: false, error: "Method not allowed" });
  }

  const result = validateEnquiry(request.body || {});
  if (!result.ok) {
    return response.status(400).json({ delivered: false, errors: result.errors });
  }

  const reference = `ENQ-${Date.now().toString(36).toUpperCase()}`;
  const message = enquiryMessage(result.value, reference);
  const delivery = await deliverEnquiry(
    { reference, enquiry: result.value, message },
    process.env,
  );

  return response.status(delivery.delivered ? 200 : 202).json({
    delivered: delivery.delivered,
    channel: delivery.channel,
    reference,
    message,
    whatsappUrl: `https://wa.me/917995022614?text=${encodeURIComponent(message)}`,
  });
};
