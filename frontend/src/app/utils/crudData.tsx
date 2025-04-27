export const getData = async (url: string) => {
  try {
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to fetch data from ${url}: ${response.statusText}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error fetching JSON data:', error);
    throw error;
  }
};

export const postData = async (url: string, data: object) => {
  try {
    const response = await fetch(url, {
      method: 'POST', // HTTP method
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data), // Convert data to JSON format
    });
    
    // Check if the response is OK (status code 200-299)
    if (!response.ok) {
      throw new Error(`Failed to post data: ${response.statusText}`);
    }
    
    // Parse the response as JSON
    const result = await response.json();
    return result;
  } catch (error) {
    console.error("Error posting data:", error);
    throw error;
  }
};